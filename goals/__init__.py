import request_handler
import models
import knowledgemap
import library
from models_goals import Goal, GoalList, GoalObjectiveExerciseProficiency, \
    GoalObjectiveWatchVideo, GoalObjectiveAnyExerciseProficiency

from google.appengine.ext import db
from api.auth.xsrf import ensure_xsrf_cookie

# TomY TODO Get rid of this
class ViewGoals(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self):

        user_data = models.UserData.current()

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
        user_data = models.UserData.current()

        # TomY TODO: Replace this with decorator
        if user_data == None:
            context = {}
            context['status'] = 'notloggedin'
            self.render_jinja2_template("goals/showgoals.html", context)
            return

        user_exercise_graph = models.UserExerciseGraph.get(user_data)
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

# a videolog was just created. update any goals the user has.
def update_goals_just_watched_video(user_data, user_video):
    update_goals(user_data, user_video, GoalObjectiveWatchVideo)

def update_goals_just_did_exercise(user_data, user_exercise, became_proficient):
    goal_data = user_data.get_goal_data()
    specific_exercises = GoalList.get_from_data(goal_data, GoalObjectiveExerciseProficiency)
    any_exercises = GoalList.get_from_data(goal_data, GoalObjectiveAnyExerciseProficiency)
    changes = []
    for ex_obj in specific_exercises:
        if ex_obj.record_progress(user_data, user_exercise):
            changes.append(ex_obj)

    if became_proficient:
        # mark off an unfinished any_exercise as complete.
        for ex_obj in any_exercises:
            if not ex_obj.is_completed:
                ex_obj.record_complete(user_exercise.exercise_model)
                changes.append(ex_obj)
                break

    db.put(changes)

def update_goals(user_data, user_entity, kind):
    goal_data = user_data.get_goal_data()
    objectives = GoalList.get_from_data(goal_data, kind)
    changes = []
    for objective in objectives:
        if objective.record_progress(user_data, user_entity):
            changes.append(objective)
    db.put(changes)
