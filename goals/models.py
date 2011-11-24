#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from models import Exercise, UserVideo, Video
import templatefilters
import datetime
from object_property import ObjectProperty

from google.appengine.ext import db
from google.appengine.ext.db import Key

class Goal(db.Model):
    title = db.StringProperty()
    created_on = db.DateTimeProperty(auto_now_add=True)
    updated_on = db.DateTimeProperty(auto_now=True)
    completed_on = db.DateTimeProperty()
    abandoned = db.BooleanProperty()
    objectives = ObjectProperty()

    @staticmethod
    def create(user_data, title, objective_descriptors):
        put_user_data = False
        if not user_data.has_current_goals:
            user_data.has_current_goals = True
            put_user_data = True

        goal_list_key = user_data.goal_list_key
        if not goal_list_key:
            # Create a parent object for all the goals & objectives
            goal_list_key = Key.from_path('GoalList', 1, parent=user_data.key())
            goal_list = GoalList(key=goal_list_key, user=user_data.user)
            goal_list.put()

            # Update UserData
            user_data.goal_list = goal_list
            put_user_data = True

        if put_user_data:
            user_data.put()

        objectives = []
        for descriptor in objective_descriptors:
            if descriptor['type'] == 'GoalObjectiveExerciseProficiency':
                objectives.append(GoalObjectiveExerciseProficiency(descriptor['exercise'], user_data))
            elif descriptor['type'] == 'GoalObjectiveWatchVideo':
                objectives.append(GoalObjectiveWatchVideo(descriptor['video'], user_data))
            elif descriptor['type'] == "GoalObjectiveAnyExerciseProficiency":
                objectives.append(GoalObjectiveAnyExerciseProficiency(description="Any exercise"))
            elif descriptor['type'] == "GoalObjectiveAnyVideo":
                objectives.append(GoalObjectiveAnyVideo(description="Any video"))

        # Create the new goal
        new_goal = Goal(parent=goal_list_key, title=title,
            objectives=objectives)
        new_goal.put()

        return new_goal

    def get_visible_data(self, user_exercise_graph):
        goal_ret = {}
        goal_ret['id'] = self.key().id()
        goal_ret['title'] = self.title
        goal_ret['objectives'] = []
        goal_ret['created'] = self.created_on
        goal_ret['created_ago'] = templatefilters.timesince_ago(self.created_on)
        goal_ret['updated'] = self.updated_on
        goal_ret['updated_ago'] = templatefilters.timesince_ago(self.updated_on)
        if self.completed_on:
            goal_ret['completed'] = self.completed_on
            goal_ret['completed_ago'] = templatefilters.timesince_ago(self.completed_on)

            td = self.completed_on - self.created_on
            completed_seconds = (td.seconds + td.days * 24 * 3600)
            goal_ret['completed_time'] = templatefilters.seconds_to_time_string(completed_seconds)

            if self.abandoned:
                goal_ret['abandoned'] = True

        for objective in self.objectives:
            objective_ret = {}
            objective_ret['type'] = objective.__class__.__name__
            objective_ret['description'] = objective.description
            objective_ret['short_display_name'] = objective._get_short_display_name()
            objective_ret['progress'] = objective.progress
            objective_ret['url'] = objective.url()
            objective_ret['internal_id'] = objective.internal_id()
            objective_ret['status'] = objective.get_status(user_exercise_graph=user_exercise_graph)
            goal_ret['objectives'].append(objective_ret)
        return goal_ret

    def record_complete(self):
        # Is this goal complete?
        if all([o.is_completed for o in self.objectives]):
            self.completed_on = datetime.datetime.now()

    def abandon(self):
        self.completed_on = datetime.datetime.now()
        self.abandoned = True

    @property
    def is_completed(self):
        return (self.completed_on is not None)

    def just_watched_video(self, user_data, user_video):
        changed = False
        specific_videos = GoalList.get_from_data(self.objectives, GoalObjectiveWatchVideo)
        for objective in specific_videos:
            if objective.record_progress(user_data, user_video):
                changed = True

        if user_video.completed:
            any_videos = GoalList.get_from_data(self.objectives, GoalObjectiveAnyVideo)
            found = False
            for vid_obj in any_videos:
                if vid_obj.video_key == str(user_video.video.key()):
                    found = True
                    break
            if not found:
                for vid_obj in any_videos:
                    if not vid_obj.is_completed:
                        vid_obj.record_complete(user_video.video)
                        changed = True
                        break

        if changed:
            self.record_complete()

        return changed

    def just_did_exercise(self, user_data, user_exercise, became_proficient):
        changed = False
        specific_exercises = GoalList.get_from_data(self.objectives, GoalObjectiveExerciseProficiency)
        for ex_obj in specific_exercises:
            if ex_obj.record_progress(user_data, user_exercise):
                changed = True

        if became_proficient:
            any_exercises = GoalList.get_from_data(self.objectives, GoalObjectiveAnyExerciseProficiency)
            found = False
            for ex_obj in any_exercises:
                if ex_obj.exercise_name == user_exercise.exercise_model.name:
                    found = True
                    break
            if not found:
                for ex_obj in any_exercises:
                    if not ex_obj.is_completed:
                        ex_obj.record_complete(user_exercise.exercise_model)
                        changed = True
                        break

        if changed:
            self.record_complete()

        return changed

# todo: think about moving these static methods to UserData. Almost all have
# user_data as the first argument.
class GoalList(db.Model):
    # todo: remove this. can't find anything that uses this user property.
    user = db.UserProperty()

    @staticmethod
    def get_from_data(data, type):
        return [entity for entity in data if isinstance(entity, type)]

    @staticmethod
    def get_current_goals(user_data, show_complete=False):
        if not user_data:
            return []

        # Fetch data from datastore
        goal_data = user_data.get_goal_data()
        goals = GoalList.get_from_data(goal_data, Goal)
        return [g for g in goals if show_complete or not g.is_completed]

    @staticmethod
    def get_visible_for_user(user_data, user_exercise_graph=None, show_complete=False):
        return [goal.get_visible_data(user_exercise_graph) for goal in
            GoalList.get_current_goals(user_data, show_complete)]

    @staticmethod
    def delete_goal(user_data, id):
        # Fetch data from datastore
        goal_data = user_data.get_goal_data()
        goals = GoalList.get_from_data(goal_data, Goal)

        for goal in goals:
            if str(goal.key().id()) == str(id):
                goal.delete()
                return True

        return False

    @staticmethod
    def delete_all_goals(user_data):
        # Fetch data from datastore
        goal_data = user_data.get_goal_data()
        goals = GoalList.get_from_data(goal_data, Goal)

        for goal in goals:
            goal.delete()

    @staticmethod
    def exercises_in_current_goals(user_data):
        goals = GoalList.get_current_goals(user_data)
        return [obj.exercise_name for g in goals for obj in g.objectives
            if obj.__class__.__name__ == 'GoalObjectiveExerciseProficiency']

    @staticmethod
    def videos_in_current_goals(user_data):
        goals = GoalList.get_current_goals(user_data)
        return [obj.video for g in goals for obj in g.objectives
            if obj.__class__.__name__ == 'GoalObjectiveWatchVideo']

def shorten(s, n=12):
    if len(s) <= n:
        return s
    chunk = (n - 3) / 2
    even = 1 - (n % 2)
    return s[:chunk + even] + '...' + s[-chunk:]

class GoalObjective(object):
    # Objective status
    progress = 0.0
    description = None
    _short_display_name = None

    def __init__(self, description):
        self.description = description

    def url():
        '''url to which the objective points when used as a nav bar.'''
        raise Exception

    def record_progress(self):
        return False

    def record_complete(self):
        self.progress = 1.0

    @property
    def is_completed(self):
        return self.progress >= 1.0

    def get_status(self, **kwargs):
        if self.is_completed:
            return "proficient"

        if self.progress > 0:
            return "started"

        return ""

    def _get_short_display_name(self):
        if self._short_display_name:
            return self._short_display_name
        else:
            return shorten(self.description)

    def _set_short_display_name(self, value):
        self._short_display_name = value

    short_display_name = property(_get_short_display_name, _set_short_display_name)

class GoalObjectiveExerciseProficiency(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    exercise_name = None

    def __init__(self, exercise, user_data):
        self.exercise_name = exercise.name
        self.description = exercise.display_name
        self.short_display_name = exercise.short_display_name
        self.progress = user_data.get_or_insert_exercise(exercise).progress

    def url(self):
        exercise = Exercise.get_by_name(self.exercise_name)
        return exercise.relative_url

    def internal_id(self):
        return self.exercise_name

    def record_progress(self, user_data, user_exercise):
        if self.exercise_name == user_exercise.exercise:
            if user_data.is_proficient_at(user_exercise.exercise):
                self.progress = 1.0
            else:
                self.progress = user_exercise.progress
            return True

        return False

    def get_status(self, user_exercise_graph=None):
        if not user_exercise_graph:
            # fall back to ['', 'started', 'proficient']
            return super(GoalObjectiveExerciseProficiency, self).get_status()

        graph_dict = user_exercise_graph.graph_dict(self.exercise_name)
        student_review_exercise_names = user_exercise_graph.review_exercise_names()
        status = ""

        if graph_dict["proficient"]:

            if self.exercise_name in student_review_exercise_names:
                status = "review"
            else:
                status = "proficient"
#                if not graph_dict["explicitly_proficient"]:
 #                   status = "Proficient (due to proficiency in a more advanced module)"

        elif graph_dict["struggling"]:
            status = "struggling"
        elif graph_dict["total_done"] > 0:
            status = "started"
        return status

class GoalObjectiveAnyExerciseProficiency(GoalObjective):
    # which exercise fulfilled this objective, set upon completion
    exercise_name = None

    def url(self):
        if self.exercise_name:
            return Exercise.get_relative_url(self.exercise_name)
        else:
            return "/exercisedashboard"

    def internal_id(self):
        return ''

    def record_complete(self, exercise):
        super(GoalObjectiveAnyExerciseProficiency, self).record_complete()
        self.exercise_name = exercise.name
        self.description = exercise.display_name
        self.short_display_name = exercise.short_display_name
        return True

class GoalObjectiveWatchVideo(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    video_key = None
    video_readable_id = None

    def __init__(self, video, user_data):
        self.video_key = str(video.key())
        self.video_readable_id = video.readable_id
        self.description = video.title

        user_video = UserVideo.get_for_video_and_user_data(video, user_data)
        if user_video:
            self.progress = user_video.progress
        else:
            self.progress = 0.0

    def url(self):
        return Video.get_relative_url(self.video_readable_id)

    def internal_id(self):
        return self.video_readable_id

    def record_progress(self, user_data, user_video):
        obj_key = db.Key(self.video_key)
        video_key = UserVideo.video.get_value_for_datastore(user_video)
        if obj_key == video_key:
            self.progress = user_video.progress
            return True
        return False

class GoalObjectiveAnyVideo(GoalObjective):
    # which video fulfilled this objective, set upon completion
    video_key = None
    video_readable_id = None

    def url(self):
        if self.video_readable_id:
            return Video.get_relative_url(self.video_readable_id)
        else:
            return "/"

    def internal_id(self):
        return ''

    def record_complete(self, video):
        super(GoalObjectiveAnyVideo, self).record_complete()
        self.video_key = str(video.key())
        self.video_readable_id = video.readable_id
        self.description = video.title
        return True
