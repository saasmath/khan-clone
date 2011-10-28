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
                GoalObjectiveExerciseProficiency.create(new_goal, descriptor['exercise'])
            if descriptor['type'] == 'GoalObjectiveWatchVideo':
                GoalObjectiveWatchVideo.create(new_goal, descriptor['video'])

        return new_goal

    def get_visible_data(self, objectives):
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
            goal_list = GoalList.get_from_data(goal_data, GoalList)[0]

            # annotate the active goal, this is icky
            for goal in goals:
                if goal.key() == GoalList.active.get_value_for_datastore(goal_list):
                    goal.active = True

            return [goal.get_visible_data(objectives) for goal in goals]

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

class GoalObjectiveExerciseProficiency(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    exercise = db.ReferenceProperty(models.Exercise)
    exercise_name = db.StringProperty()

    @staticmethod
    def create(parent_goal, exercise):
        new_objective = GoalObjectiveExerciseProficiency(parent_goal)
        new_objective.exercise = exercise
        new_objective.exercise_name = exercise.name
        new_objective.description = models.Exercise.to_display_name(exercise.name)
        new_objective.put()
        return new_objective

    def url(self):
        return self.exercise.relative_url

class GoalObjectiveWatchVideo(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    video = db.ReferenceProperty(models.Video)

    @staticmethod
    def create(parent_goal, video):
        new_objective = GoalObjectiveWatchVideo(parent_goal)
        new_objective.video = video
        new_objective.description = video.title
        new_objective.put()
        return new_objective

    def url(self):
        return self.video.ka_url
