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

        exercise = models.Exercise.get_by_name(exid)

        if not exercise:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        user_exercise = user_data.get_or_insert_exercise(exercise)

        # TODO(kamens): this specific user_exercise stuff should all be going away
        # Cache these so we don't have to worry about future lookups
        user_exercise.exercise_model = exercise
        user_exercise._user_data = user_data
        user_exercise._user_exercise_graph = user_exercise_graph
        user_exercise.summative = exercise.summative

        user_exercise.exercise_model.related_videos = [exercise_video.video for exercise_video in exercise.related_videos_fetch()]
        for video in user_exercise.exercise_model.related_videos:
            video.id = video.key().id()

        next_user_exercises = models.UserTopic.next_user_exercises()

        # TODO(kamens): get rid of the need to do this gross perf hack
        for next_user_exercise in next_user_exercises:
            next_exercise = models.Exercise.get_by_name(next_user_exercise.exercise)

            next_exercise.related_videos = [exercise_video.video for exercise_video in next_exercise.related_videos_fetch()]
            for video in next_exercise.related_videos:
                video.id = video.key().id()

            next_user_exercise.exercise_model = next_exercise

        stack = get_problem_stack(next_user_exercises)

        template_values = {
            "user_exercise": user_exercise,
            "stack_json": jsonify(stack, camel_cased=True),
            "user_exercises_json": jsonify(next_user_exercises, camel_cased=True),
            # TODO(kamens): this is going away
            "user_exercise_json": jsonify(user_exercise),
        }

        self.render_jinja2_template("exercises/exercise_template.html", template_values)
