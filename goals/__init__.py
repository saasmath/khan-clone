from __future__ import absolute_import

import request_handler
from models import (UserData, UserExerciseGraph, UserExercise, Exercise,
    Video, VideoLog)
import knowledgemap
import library
import user_util
import datetime
import random
import logging
import exercises
from .models import (Goal, GoalList, GoalObjective,
    GoalObjectiveExerciseProficiency, GoalObjectiveAnyExerciseProficiency,
    GoalObjectiveWatchVideo, GoalObjectiveAnyVideo)

from google.appengine.api import users
from google.appengine.ext import db
from api.auth.xsrf import ensure_xsrf_cookie

# TomY TODO Get rid of this
class ViewGoals(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self):

        user_data = UserData.current()

        context = {}

        if user_data == None:
            context['status'] = 'notloggedin'
            self.render_jinja2_template("goals/showgoals.html", context)
            return

        context['status'] = 'none'
        context['goals'] = GoalList.get_visible_for_user(user_data)
        context['goals_count'] = len(context['goals'])
        self.render_jinja2_template("goals/showgoals.html", context)

class CreateNewGoal(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self):
        user_data = UserData.current()

        # TomY TODO: Replace this with decorator
        if user_data == None:
            context = {}
            context['status'] = 'notloggedin'
            self.render_jinja2_template("goals/showgoals.html", context)
            return

        user_exercise_graph = UserExerciseGraph.get(user_data)
        if user_data.reassess_from_graph(user_exercise_graph):
            user_data.put() # TomY TODO copied from exercises.py; is this necessary here?

        graph_dicts = user_exercise_graph.graph_dicts()
        suggested_graph_dicts = user_exercise_graph.suggested_graph_dicts()
        proficient_graph_dicts = user_exercise_graph.proficient_graph_dicts()
        recent_graph_dicts = user_exercise_graph.recent_graph_dicts()
        review_graph_dicts = user_exercise_graph.review_graph_dicts()

        for graph_dict in suggested_graph_dicts:
            graph_dict["status"] = "Suggested"

        for graph_dict in proficient_graph_dicts:
            graph_dict["status"] = "Proficient"

        for graph_dict in review_graph_dicts:
            graph_dict["status"] = "Review"

            try:
                suggested_graph_dicts.remove(graph_dict)
            except ValueError:
                pass

        # Get pregenerated library content from our in-memory/memcache two-layer cache
        library_content = library.library_content_html()

        context = {
            'graph_dicts': graph_dicts,
            'suggested_graph_dicts': suggested_graph_dicts,
            'recent_graph_dicts': recent_graph_dicts,
            'review_graph_dicts': review_graph_dicts,
            'user_data': user_data,
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
                Goal.create(user_data, user_data.get_goal_data(), title, objective_descriptors)

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

def goals_with_objectives(user_data):
    goal_data = user_data.get_goal_data()
    return GoalList.get_from_data(goal_data, Goal)

# a videolog was just created. update any goals the user has.
def update_goals_just_watched_video(user_data, user_video):
    changes = []
    for goal in goals_with_objectives(user_data):
        changed = False
        specific_videos = GoalList.get_from_data(goal.objectives, GoalObjectiveWatchVideo)
        for objective in specific_videos:
            if objective.record_progress(user_data, goal, user_video):
                changed = True

        any_videos = GoalList.get_from_data(goal.objectives, GoalObjectiveAnyVideo)
        if user_video.completed:
            for vid_obj in any_videos:
                if not vid_obj.is_completed:
                    vid_obj.record_complete(user_video.video, goal)
                    changed = True
                    break
        if changed:
            changes.append(goal)

    if changes:
        db.put(changes)

def update_goals_just_did_exercise(user_data, user_exercise, became_proficient):
    changes = []
    for goal in goals_with_objectives(user_data):
        changed = False

        specific_exercises = GoalList.get_from_data(goal.objectives, GoalObjectiveExerciseProficiency)
        for ex_obj in specific_exercises:
            if ex_obj.record_progress(user_data, goal, user_exercise):
                changed = True

        any_exercises = GoalList.get_from_data(goal.objectives, GoalObjectiveAnyExerciseProficiency)
        if became_proficient:
            # mark off an unfinished any_exercise as complete.
            for ex_obj in any_exercises:
                if not ex_obj.is_completed:
                    ex_obj.record_complete(user_exercise.exercise_model, goal)
                    changed = True
                    break
        if changed:
            changes.append(goal)

    if changes:
        db.put(changes)
