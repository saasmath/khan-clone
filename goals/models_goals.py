#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import models
import logging

from google.appengine.ext import db
from google.appengine.ext.db import polymodel, Key

class Goal(db.Model):
    title = db.StringProperty()
    active = False

    @staticmethod
    def create(user_data, goal_data, title, objective_descriptors):
        parent_list = GoalList.get_from_data(goal_data, GoalList)
        if not parent_list:
            # Create a parent object for all the goals & objectives
            key = Key.from_path('GoalList', 1, parent=user_data.key())
            goal_list = GoalList.get_or_insert(str(key), user=user_data.user)

            # Update UserData
            user_data.goal_list = goal_list
            user_data.put()
        else:
            goal_list = parent_list[0]

        # Create the new goal
        new_goal = Goal(goal_list)
        new_goal.title = title
        new_goal.put()

        # Set the goal active
        goal_list.active = new_goal
        goal_list.put()

        for descriptor in objective_descriptors:
            if descriptor['type'] == 'GoalObjectiveExerciseProficiency':
                GoalObjectiveExerciseProficiency.create(new_goal, descriptor['exercise'], user_data)
            if descriptor['type'] == 'GoalObjectiveWatchVideo':
                GoalObjectiveWatchVideo.create(new_goal, descriptor['video'], user_data)

        return new_goal

    def get_visible_data(self, objectives, user_exercise_graph):
        goal_ret = {}
        goal_ret['id'] = self.key().id()
        goal_ret['title'] = self.title
        goal_ret['objectives'] = []
        goal_ret['active'] = self.active
        for objective in objectives:
            if objective.parent_key() == self.key():
                objective_ret = {}
                objective_ret['type'] = objective.class_name()
                objective_ret['description'] = objective.description
                objective_ret['progress'] = objective.progress
                objective_ret['url'] = objective.url()
                objective_ret['status'] = objective.getStatus(user_exercise_graph)
                goal_ret['objectives'].append(objective_ret)
        return goal_ret

    def get_objectives(self, data):
        return [entity for entity in data if isinstance(entity, GoalObjective) and entity.parent_key() == self.key()]

class GoalList(db.Model):
    user = db.UserProperty()
    active = db.ReferenceProperty(Goal)

    @staticmethod
    def get_from_data(data, type):
        return [entity for entity in data if isinstance(entity, type)]

    @staticmethod
    def get_visible_for_user(user_data, user_exercise_graph = None):
        if user_data:
            # Fetch data from datastore
            goal_data = user_data.get_goal_data()
            if len(goal_data) == 0:
                return None

            goals = GoalList.get_from_data(goal_data, Goal)
            objectives = GoalList.get_from_data(goal_data, GoalObjective)
            goal_list = GoalList.get_from_data(goal_data, GoalList)[0]

            # annotate the active goal, this is icky
            for goal in goals:
                if goal.key() == GoalList.active.get_value_for_datastore(goal_list):
                    goal.active = True

            return [goal.get_visible_data(objectives, user_exercise_graph) for goal in goals]

        return None

    @staticmethod
    def delete_goal(user_data, id):
        # Fetch data from datastore
        goal_data = user_data.get_goal_data()
        goals = GoalList.get_from_data(goal_data, Goal)

        for goal in goals:
            if str(goal.key().id()) == str(id):
                children = goal.get_objectives(goal_data)
                for child in children:
                    child.delete()
                goal.delete()
                return True

        return False

    @staticmethod
    def delete_all_goals(user_data):
        # Fetch data from datastore
        goal_data = user_data.get_goal_data()
        goals = GoalList.get_from_data(goal_data, Goal)

        for goal in goals:
            children = goal.get_objectives(goal_data)
            for child in children:
                child.delete()
            goal.delete()

    @staticmethod
    def activate_goal(user_data, id):
        # Fetch data from datastore
        goal_data = user_data.get_goal_data()
        goal_list = GoalList.get_from_data(goal_data, GoalList)[0]
        goals = GoalList.get_from_data(goal_data, Goal)

        id = int(id)
        for goal in goals:
            if goal.key().id() == id:
                goal_list.active = goal
                goal_list.put()
                return True

        return False

class GoalObjective(polymodel.PolyModel):
    # Objective status
    progress = db.FloatProperty(default=0.0)
    description = db.StringProperty()

    def url():
        '''url to which the objective points when used as a nav bar.'''
        raise Exception

    def record_progress(self):
        return False

    def record_complete(self):
        self.progress = 1.0
        return True

class GoalObjectiveExerciseProficiency(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    exercise = db.ReferenceProperty(models.Exercise)

    @staticmethod
    def create(parent_goal, exercise, user_data):
        new_objective = GoalObjectiveExerciseProficiency(parent_goal)
        new_objective.exercise = exercise
        new_objective.description = models.Exercise.to_display_name(exercise.name)

        new_objective.progress = user_data.get_or_insert_exercise(exercise).progress

        new_objective.put()
        return new_objective

    def url(self):
        return self.exercise.relative_url

    def record_progress(self, user_data, user_exercise):
        if self.exercise.key() == user_exercise.exercise_model.key():
            if user_data.is_proficient_at(user_exercise.exercise):
                self.progress = 1.0
            else:
                self.progress = user_exercise.progress
            return True
        return False

    def getStatus(self, user_exercise_graph):
        if not user_exercise_graph:
            return ""

        exercise_name = self.exercise.name
        graph_dict = user_exercise_graph.graph_dict(exercise_name)
        student_review_exercise_names = user_exercise_graph.review_exercise_names()
        status = ""

        if graph_dict["proficient"]:

            if exercise_name in student_review_exercise_names:
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

class GoalObjectiveWatchVideo(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    video = db.ReferenceProperty(models.Video)

    @staticmethod
    def create(parent_goal, video, user_data):
        new_objective = GoalObjectiveWatchVideo(parent_goal)
        new_objective.video = video
        new_objective.description = video.title

        user_video = models.UserVideo.get_for_video_and_user_data(video, user_data)
        new_objective.progress = user_video.progress

        new_objective.put()
        return new_objective

    def url(self):
        return self.video.ka_url

    def record_progress(self, user_data, user_video):
        obj_key = GoalObjectiveWatchVideo.video.get_value_for_datastore(self)
        video_key = models.UserVideo.video.get_value_for_datastore(user_video)
        if obj_key == video_key:
            self.progress = user_video.progress
            return True
        return False

    def getStatus(self, user_exercise_graph):
        if self.progress == 1.0:
            return "proficient"

        if self.progress > 0:
            return "started"

        return ""
