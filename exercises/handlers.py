import logging

import request_handler
import models
from exercises.stacks import get_problem_stack
from api.jsonify import jsonify
from api.auth.xsrf import ensure_xsrf_cookie

class ViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, exid=None):

        # TODO(kamens): error/permission handling, past problem viewing,
        #  and the rest of exercises/__init__.py's ViewExercise edge cases

        review_mode = self.request.path == "/review" 

        if not exid and not review_mode:
            self.redirect("/exercise/%s" % self.request_string("exid", default="addition_1"))
            return

        if not models.Exercise.get_by_name(exid) and not review_mode:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)
        user_exercises = models.UserTopic.next_user_exercises(review_mode=review_mode)

        if len(user_exercises) == 0:
            # If something has gone wrong and we didn't get any UserExercises,
            # somebody could've hit the /review URL without any review problems
            # or we hit another issue. Send 'em back to the dashboard for now.
            self.redirect("/exercisedashboard")
            return

        stack = get_problem_stack(user_exercises, no_extra_cards=review_mode)

        template_values = {
            "stack_json": jsonify(stack, camel_cased=True),
            "user_exercises_json": jsonify(user_exercises, camel_cased=True),
            "review_mode_json": jsonify(review_mode),
        }

        self.render_jinja2_template("exercises/exercise_template.html", template_values)
