import logging

import request_handler
import models
from exercises.stacks import get_problem_stack
from api.jsonify import jsonify
from api.auth.xsrf import ensure_xsrf_cookie

class ViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, exid=None):

        # TODO(kamens): review mode in this handler, error handling, past problem viewing
        # ...all of exercises/__init__.py's ViewExercise edge cases

        if not exid:
            self.redirect("/exercise/%s" % self.request_string("exid", default="addition_1"))
            return

        if not models.Exercise.get_by_name(exid):
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        user_exercises = models.UserTopic.next_user_exercises()
        stack = get_problem_stack(user_exercises)

        template_values = {
            "stack_json": jsonify(stack, camel_cased=True),
            "user_exercises_json": jsonify(user_exercises, camel_cased=True),
        }

        self.render_jinja2_template("exercises/exercise_template.html", template_values)
