import request_handler
import models
import knowledgemap
import library
import logging
from models_goals import Goal, GoalList, GoalObjective, GoalObjectiveExerciseProficiency, GoalObjectiveWatchVideo

from google.appengine.ext import db

class ViewGoals(request_handler.RequestHandler):

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

class CreateGoal(request_handler.RequestHandler):

    def get(self):
        user_data = models.UserData.current()

        context = {}

        if user_data == None:
            context['status'] = 'notloggedin'
            self.render_jinja2_template("goals/showgoals.html", context)
            return

        context['status'] = 'none'
        context['goals'] = GoalList.get_visible_for_user(user_data)

        goal_data = user_data.get_goal_data()

        objectives = []
        objective_descriptors = []
        fail_validation = False
        valid_count = 0

        if not self.request.get('title'):
            logging.error("Error creating new goal: Invalid title")
            fail_validation = True

        for idx in xrange(1,10):
            base_str = 'objective'+str(idx)
            if self.request.get(base_str+'_type'):
                objective_descriptor = {}
                objective_descriptor['type'] = self.request.get(base_str+'_type');
                objective_descriptors.append(objective_descriptor)

                if objective_descriptor['type'] == 'exercise_proficiency':
                    objective_descriptor['exercise'] = models.Exercise.get_by_name(self.request.get(base_str+'_exercise'))
                    if not objective_descriptor['exercise']:
                        fail_validation = True
                        logging.error("Error creating new goal: Could not find exercise " + self.request.get(base_str+'_exercise'))
                    else:
                        valid_count += 1

                if objective_descriptor['type'] == 'watch_video':
                    objective_descriptor['video'] = models.Video.get_for_readable_id(self.request.get(base_str+'_video'))
                    if not objective_descriptor['video']:
                        fail_validation = True
                        logging.error("Error creating new goal: Could not find video " + self.request.get(base_str+'_video'))
                    else:
                        valid_count += 1

        if valid_count == 0:
            fail_validation = True
            logging.error("Error creating new goal: No objectives specified")

        if fail_validation:
            context['status'] = 'failed';
        else:
            new_goal = Goal.create(user_data, goal_data, self.request.get('title')) 

            for descriptor in objective_descriptors:
                new_objective = None

                if descriptor['type'] == 'exercise_proficiency':
                    new_objective = GoalObjectiveExerciseProficiency.create(new_goal, descriptor['exercise'])
                if descriptor['type'] == 'watch_video':
                    new_objective = GoalObjectiveWatchVideo.create(new_goal, descriptor['video'])
                if new_objective:
                    objectives.append(new_objective)

            context['goals'].append(new_goal.get_visible_data(objectives))
            context['status'] = 'success'

        context['goals_count'] = len(context['goals'])
        self.render_jinja2_template("goals/showgoals.html", context)

class DeleteGoal(request_handler.RequestHandler):

    def get(self):
        user_data = models.UserData.current()

        context = {}
        if user_data == None:
            context['status'] = 'notloggedin'
            self.render_jinja2_template("goals/showgoals.html", context)
            return

        context['status'] = 'none'
        context['goals'] = GoalList.get_visible_for_user(user_data)

        goal_data = user_data.get_goal_data()

        objectives = []
        objective_descriptors = []

        goal_to_delete = self.request.get('id')
        GoalList.delete_goal(user_data, goal_to_delete)

        for goal in context['goals']:
            if str(goal['id']) == str(goal_to_delete):
                context['goals'].remove(goal)
                break;

        context['goals_count'] = len(context['goals'])
        self.render_jinja2_template("goals/showgoals.html", context)

