#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import models
import logging

from google.appengine.ext import db

class Goal(db.Model):
    title = db.StringProperty()

    @staticmethod
    def create(userdata, goal_data, title, objective_descriptors):
        return db.run_in_transaction(Goal.create_internal, userdata, goal_data, title, objective_descriptors)

    @staticmethod
    def create_internal(userdata, goal_data, title, objective_descriptors):
        parent_list = GoalList.get_from_data(goal_data, GoalList)
        if not parent_list:
            # Create a parent object for all the goals & objectives
            parent_obj = GoalList(userdata)
            parent_obj.user = userdata.user
            parent_obj.put()

            # Update UserData
            userdata.goal_list = parent_obj
            userdata.put()
        else:
            parent_obj = parent_list[0]

        # Create the new goal
        new_goal = Goal(parent_obj)
        new_goal.title = title
        new_goal.put()

        for descriptor in objective_descriptors:
            if descriptor['type'] == 'exercise_proficiency':
                GoalObjectiveExerciseProficiency.create(new_goal, descriptor['exercise'])
            if descriptor['type'] == 'watch_video':
                GoalObjectiveWatchVideo.create(new_goal, descriptor['video'])

        return new_goal

    def get_visible_data(self, objectives):
        goal_ret = {}
        goal_ret['id'] = self.key().id()
        goal_ret['title'] = self.title
        goal_ret['objectives'] = []
        for objective in objectives:
            if objective.parent_key() == self.key():
                objective_ret = {}
                objective_ret['type'] = objective.type()
                objective_ret['description'] = objective.description()
                objective_ret['progress'] = objective.progress()
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
    def get_visible_for_user(user_data):
        if user_data:
            # Fetch data from datastore
            goal_data = user_data.get_goal_data()
            goals = GoalList.get_from_data(goal_data, Goal)
            objectives = GoalList.get_from_data(goal_data, GoalObjective)

            goals_ret = []

            for goal in goals:
                # Copy goals and sort objectives by goal
                goals_ret.append(goal.get_visible_data(objectives))

            return goals_ret

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
                break
        return

class GoalObjective():
    def type(self):
        return '';

    def description(self):
        return '';

    def progress(self):
        return 0;

class GoalObjectiveExerciseProficiency(db.Model, GoalObjective):
    # Objective definition (Chosen at goal creation time)
    exercise = db.ReferenceProperty(models.Exercise)
    exercise_display_name = db.StringProperty()
    # Objective status
    completion = db.FloatProperty()

    @staticmethod
    def create(parent_goal, exercise):
        new_objective = GoalObjectiveExerciseProficiency(parent_goal)
        new_objective.exercise = exercise
        new_objective.exercise_display_name = models.Exercise.to_display_name(exercise.name)
        new_objective.put()
        return new_objective

    def type(self):
        return 'exercise_proficiency';

    def description(self):
        return self.exercise_display_name;

    def progress(self):
        if self.completion == None:
            return 0
        return self.completion

class GoalObjectiveWatchVideo(db.Model, GoalObjective):
    # Objective definition (Chosen at goal creation time)
    video = db.ReferenceProperty(models.Video)
    video_title = db.StringProperty()
    # Objective status
    completion = db.FloatProperty()

    @staticmethod
    def create(parent_goal, video):
        new_objective = GoalObjectiveWatchVideo(parent_goal)
        new_objective.video = video
        new_objective.video_title = video.title
        new_objective.put()
        return new_objective

    def type(self):
        return 'watch_video';

    def description(self):
        return self.video_title;

    def progress(self):
        if self.completion == None:
            return 0
        return self.completion

