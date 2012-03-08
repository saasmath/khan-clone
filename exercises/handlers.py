import logging
import urllib

import request_handler
import models
from exercises.stacks import get_problem_stack, get_review_stack
from api.jsonify import jsonify
from api.auth.xsrf import ensure_xsrf_cookie

class ViewExerciseDeprecated(request_handler.RequestHandler):

    def get(self, exid=None):

        exercise = models.Exercise.get_by_name(exid)

        if not exercise:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        topic = exercise.first_topic()

        if not topic:
            raise MissingExerciseException("Exercise '%s' is missing a topic" % exid)

        self.redirect("/%s/e/%s" % (topic.get_extended_slug(), urllib.quote(exid)))

class ViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, path, exid=None):

        # TODO(kamens): error/permission handling, past problem viewing,
        #  and the rest of exercises/__init__.py's ViewExercise edge cases

        review_mode = "review" == path
        practice_mode = bool(exid)

        topic = None
        exercise = None
        user_exercises = None

        if not review_mode:

            path_list = path.split('/')
            topic_id = path_list[-1]

            if len(topic_id) > 0:
                topic = models.Topic.get_by_id(topic_id)

            # Topics are required
            if not topic:
                raise MissingExerciseException("Exercise '%s' is missing a topic" % exid)

            if exid:
                exercise = models.Exercise.get_by_name(exid)

                # Exercises are not required but must be valid if supplied
                if not exercise:
                    raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        if practice_mode:
            # Practice mode involves a single exercise only
            user_exercises = [user_data.get_or_insert_exercise(exercise)]
        else:
            # Topics mode context switches between multiple exercises
            user_exercises = models.UserExercise.next_in_topic(user_data, topic)

        if len(user_exercises) == 0:
            # If something has gone wrong and we didn't get any UserExercises,
            # somebody could've hit the /review URL without any review problems
            # or we hit another issue. Send 'em back to the dashboard for now.
            self.redirect("/exercisedashboard")
            return

        stack = get_review_stack(user_exercises) if review_mode else get_problem_stack(user_exercises)

        template_values = {
            "stack_json": jsonify(stack, camel_cased=True),
            "user_exercises_json": jsonify(user_exercises, camel_cased=True),
            "review_mode_json": jsonify(review_mode, camel_cased=True),
            "practice_mode_json": jsonify(practice_mode, camel_cased=True),
            "topic_json": jsonify(topic, camel_cased=True),
            "exercise_json": jsonify(exercise, camel_cased=True),
            "user_data_json": jsonify(user_data, camel_cased=True),
        }

        self.render_jinja2_template("exercises/exercise_template.html", template_values)
