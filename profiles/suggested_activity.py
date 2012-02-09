import datetime

import models


class SuggestedActivity(object):
    """ Suggested activity for a user...?

        Haiku for you:

        Now, exercises.
        Soon, video, goal, and yes,
        perhaps badges! Help!
    """

    @staticmethod
    def get_for(user_data):
        return {
            "exercises": SuggestedActivity.get_exercises_for(user_data),
            "videos": SuggestedActivity.get_videos_for(user_data),
            "goals": SuggestedActivity.get_goals_for(user_data),
        }

    @staticmethod
    def get_videos_for(user_data):
        # Not sure how this will work if we're iterating through videologs
        # and separating them into either suggested or recent.
        return []

    @staticmethod
    def get_goals_for(user_data):
        return []

    @staticmethod
    def get_exercises_for(user_data):
        user_exercise_graph = models.UserExerciseGraph.get(user_data)
        exercise_graph_dicts = user_exercise_graph.suggested_graph_dicts()

        activities = []

        for graph_dict in exercise_graph_dicts:
            activities.append(SuggestedActivity.from_exercise(graph_dict))

        return activities

    @staticmethod
    def from_exercise(exercise_graph_dict):
        activity = SuggestedActivity()
        activity.name = exercise_graph_dict["display_name"]
        activity.url = models.Exercise.get_relative_url(exercise_graph_dict["name"])
        return activity
