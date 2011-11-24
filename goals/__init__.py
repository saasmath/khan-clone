# -*- coding: utf-8 -*-

from __future__ import absolute_import
import datetime
import random
import logging

from google.appengine.api import users
from google.appengine.ext import db

import request_handler
import knowledgemap
import library
import user_util
import exercises
from api.auth.xsrf import ensure_xsrf_cookie
from phantom_users.phantom_util import create_phantom
from models import UserData, UserExercise, Exercise, Video, VideoLog
from .models import (Goal, GoalList, GoalObjective,
    GoalObjectiveExerciseProficiency, GoalObjectiveAnyExerciseProficiency,
    GoalObjectiveWatchVideo, GoalObjectiveAnyVideo)


class CreateNewGoal(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    @create_phantom
    def get(self):
        user_data = UserData.current()

        # Get pregenerated library content from our in-memory/memcache two-layer cache
        library_content = library.library_content_html()

        context = {
            'graph_dict_data': exercises.exercise_graph_dict_json(user_data),
            'user_data': user_data,
            'need_maps_package': self.request_bool('need_maps_package', default=True),
            'expanded_all_exercises': user_data.expanded_all_exercises,
            'map_coords': knowledgemap.deserializeMapCoords(user_data.map_coords),
            'library_content': library_content,
        }
        self.render_jinja2_template("goals/creategoal.html", context)

class CreateRandomGoalData(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        login_user = UserData.current()
        exercises_list = [exercise for exercise in Exercise.all()]
        videos_list = [video for video in Video.all()]

        first_names = [ "Aston", "Stratford", "Leanian", "Patwin", "Renaldo", "Welford", "Maher", "Gregorio", "Roth", "Gawain", "Fiacre", "Coillcumhann", "Honi", "Westcot", "Walden", "Onfroi", "Merlow", "Atol", "Gimm", "Dumont", "Weorth", "Corcoran", "Sinley", "Perekin", "Galt", "Tequiefah", "Zina", "Hemi Skye", "Adelie", "Afric", "Laquinta", "Molli", "Cimberleigh", "Morissa", "Alastriona", "Ailisa", "Leontina", "Aruba", "Marilda", "Ascencion", "Lidoine", "Winema", "Eraman", "Karline", "Edwinna", "Yseult", "Florencia", "Bethsaida", "Aminah", "Onida" ]
        last_names = [ "Smith", "Jackson", "Martin", "Brown", "Roy", "Tremblay", "Lee", "Gagnon", "Wilson", "Clark", "Johnson", "White", "Williams", "Taylor", "Campbell", "Anderson", "Cooper", "Jones", "Lambert" ]

        user_count = 35
        for user_id in xrange(0,user_count):
            # Create a new user
            first_name = random.choice(first_names)
            nickname = first_name + ' ' + random.choice(last_names)
            email = 'test_'+str(user_id)+'@automatedrandomdata'
            user = users.User(email)

            logging.info("Creating user " + nickname + ": (" + str(user_id+1) + "/" + str(user_count) + ")")

            user_data = UserData.get_or_insert(
                key_name="test_user_"+str(user_id),
                user=user,
                current_user=user,
                user_id=str(user_id),
                moderator=False,
                last_login=datetime.datetime.now(),
                proficient_exercises=[],
                suggested_exercises=[],
                need_to_reassess=True,
                points=0,
                coaches=[],
                user_email=email
                )
            user_data.user_nickname=nickname
            user_data.coaches = [ login_user.user_email ]
            user_data.badges = ''
            user_data.all_proficient_exercises = ''
            user_data.proficient_exercises = ''
            user_data.videos_completed = 0
            user_data.points = 0
            user_data.total_seconds_watched = 0
            user_data.put()

            # Delete user exercise & video progress
            query = UserExercise.all()
            query.filter('user = ', user)
            for user_exercise in query:
                user_exercise.delete()

            query = VideoLog.all()
            query.filter('user = ', user)
            for user_video in query:
                user_video.delete()

            # Delete existing goals
            GoalList.delete_all_goals(user_data)

            for goal_idx in xrange(1,random.randint(-1,4)):
                # Create a random goal
                objective_descriptors = []

                for objective in xrange(1,random.randint(2,4)):
                    objective_descriptors.append({ 'type': 'GoalObjectiveExerciseProficiency', 'exercise': random.choice(exercises_list) })

                for objective in xrange(1,random.randint(2,4)):
                    objective_descriptors.append({ 'type': 'GoalObjectiveWatchVideo', 'video': random.choice(videos_list) })

                title = first_name + "'s Goal #" + str(goal_idx)
                logging.info("Creating goal " + title)

                objectives = GoalObjective.from_descriptors(objective_descriptors)
                goal = Goal(parent=GoalList.ensure_goal_list(user_data),
                    title=title, objectives=objectives)
                goal.put()

                for objective in objective_descriptors:
                    if objective['type'] == 'GoalObjectiveExerciseProficiency':
                        user_exercise = user_data.get_or_insert_exercise(objective['exercise'])
                        chooser = random.randint(1,120)
                        if chooser < 60:
                            if chooser > 15:
                                count = 1
                                hints = 0
                            else:
                                if chooser < 7:
                                    count = 20
                                    hints = 0
                                else:
                                    count = 25
                                    hints = 1
                            logging.info("Starting exercise: " + objective['exercise'].name + " (" + str(count) + " problems " + str(hints*count) + " hints)")
                            for problem_number in xrange(1,count):
                                exercises.attempt_problem(user_data, user_exercise, problem_number, 1, 'TEST', 'TEST', 'TEST', True, hints, 0, "TEST", 'TEST', '0.0.0.0')

                    elif objective['type'] == 'GoalObjectiveWatchVideo':
                        seconds = random.randint(1,1200)
                        logging.info("Watching " + str(seconds) + " seconds of video " + objective['video'].title)
                        VideoLog.add_entry(user_data, objective['video'], seconds, 0, detect_cheat=False)

        #self.redirect('/')
        self.response.out.write('OK')

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
