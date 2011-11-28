# -*- coding: utf-8 -*-

from __future__ import absolute_import

from google.appengine.ext import db

from .models import GoalList

def update_goals_just_watched_video(user_data, user_video):
    fn = lambda goal: goal.just_watched_video(user_data, user_video)
    return update_goals(user_data, fn)

def update_goals_just_did_exercise(user_data, user_exercise, became_proficient):
    fn = lambda goal: goal.just_did_exercise(user_data, user_exercise,
        became_proficient)
    return update_goals(user_data, fn)

def update_goals(user_data, activity_fn):
    if not user_data.has_current_goals:
        return False

    goals = GoalList.get_current_goals(user_data)
    changes = []
    for goal in goals:
        if activity_fn(goal):
            changes.append(goal)
    if changes:
        # check to see if all goals are closed
        user_changes = []
        if all([g.completed for g in goals]):
            user_data.has_current_goals = False
            user_changes = [user_data]
        db.put(changes + user_changes)
    return changes
