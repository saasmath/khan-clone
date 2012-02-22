import logging

import request_handler
import models
from api.jsonify import jsonify
from api.auth.xsrf import ensure_xsrf_cookie

class ViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, exid):

        exercise = models.Exercise.get_by_name(exid)

        if not exercise:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        template_values = {
            "exercise": exercise,
            "exercise_json": jsonify(exercise, camel_cased=True)
        }

        self.render_jinja2_template("exercises/power_template.html", template_values)
