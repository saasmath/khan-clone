import logging

import request_handler
import models
from exercises.stacks import get_problem_stack
from api.jsonify import jsonify
from api.auth.xsrf import ensure_xsrf_cookie

class ViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, exid):

        # TODO(kamens): review mode in this handler, error handling, past problem viewing
        # ...all of exercises/__init__.py's ViewExercise edge cases

        exercise = models.Exercise.get_by_name(exid)

        if not exercise:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        exercise = models.Exercise.get_by_name(exid)

        if not exercise:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_exercise = user_data.get_or_insert_exercise(exercise)

        # Cache these so we don't have to worry about future lookups
        user_exercise.exercise_model = exercise
        user_exercise.exercise_model.sha1 = "TODO(kamens) seriously, SHA1s have been broken in reviews for a long time."
        user_exercise._user_data = user_data
        user_exercise._user_exercise_graph = user_exercise_graph
        user_exercise.summative = exercise.summative

        # Temporarily work around in-app memory caching bug
        # TODO(kamens): does this bug still exist? Here's hoping we don't hang user_exercise off of exercise any more, but we might.
        exercise.user_exercise = None

        stack = get_problem_stack(exercise)

        template_values = {
            "exercise": exercise,
            "user_exercise": user_exercise,
            "stack_json": jsonify(stack),
            "exercise_json": jsonify(exercise, camel_cased=True),
            "user_exercise_json": jsonify(user_exercise), # TODO(kamens): need camelCase agreement here
        }

        self.render_jinja2_template("exercises/power_template.html", template_values)
