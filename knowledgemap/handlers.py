# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from gae_bingo.gae_bingo import bingo, ab_test

import models
import request_handler
import knowledgemap
from exercises import exercise_graph_dict_json

class ViewKnowledgeMap(request_handler.RequestHandler):

    def get(self):
        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        show_review_drawer = (not user_exercise_graph.has_completed_review())

        template_values = {
            'graph_dict_data': exercise_graph_dict_json(user_data),
            'user_data': user_data,
            'expanded_all_exercises': user_data.expanded_all_exercises,
            'map_coords': json.dumps(knowledgemap.deserializeMapCoords(user_data.map_coords)),
            'selected_nav_link': 'practice',
            'show_review_drawer': show_review_drawer,
        }

        if show_review_drawer:
            template_values['review_statement'] = 'Attain mastery'
            template_values['review_call_to_action'] = "I'll do it"

        bingo('suggested_activity_exercises_landing')

        self.render_jinja2_template('viewexercises.html', template_values)

class SaveExpandedAllExercises(request_handler.RequestHandler):
    def post(self):
        user_data = models.UserData.current()

        if user_data:
            expanded = self.request_bool("expanded")

            user_data.expanded_all_exercises = expanded
            user_data.put() 

class SaveMapCoords(request_handler.RequestHandler):

    def get(self):
        return

    def post(self):
        user_data = models.UserData.current()

        if user_data:
            try:
                lat = self.request_float("lat")
                lng = self.request_float("lng")
                zoom = self.request_int("zoom")
            except ValueError:
                # If any of the above values aren't present in request, don't try to save.
                return

            user_data.map_coords = knowledgemap.serializeMapCoords(lat, lng, zoom)
            user_data.put()


