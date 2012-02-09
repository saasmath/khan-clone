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
        user_exercise_graph = models.UserExerciseGraph.get(user_data)
        exercise_graph_dicts = sorted(user_exercise_graph.graph_dicts(),
                                    reverse=True,
                                    key=lambda graph_dict: graph_dict["last_done"])

        min_date = datetime.datetime.min
        activities = []

        for graph_dict in exercise_graph_dicts:
            if graph_dict["last_done"] == min_date:
                break
            if not graph_dict["proficient"]:
                activities.append(SuggestedActivity.from_exercise(graph_dict))

        return activities

    @staticmethod
    def from_exercise(exercise_graph_dict):
        activity = SuggestedActivity()
        activity.name = exercise_graph_dict["display_name"]
        activity.url = models.Exercise.get_relative_url(exercise_graph_dict["name"])
        return activity
