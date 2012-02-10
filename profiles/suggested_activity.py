from profiles import recent_activity
import models


class SuggestedActivity(object):
    """ Suggested activity for a user...?

        Haiku for you:

        Now, exercises.
        Soon, video, goal, and yes,
        perhaps badges! Help!
    """

    @staticmethod
    def get_for(user_data, recent_activities=[]):
        return {
            "exercises": SuggestedActivity.get_exercises_for(user_data),
            "videos": SuggestedActivity.get_videos_for(user_data,
                                                       recent_activities),
            "goals": SuggestedActivity.get_goals_for(user_data),
        }

    @staticmethod
    def get_videos_for(user_data, recent_activities):
        recent_incomplete_videos = filter(
	            lambda entry:
	                    (entry.__class__ == recent_activity.RecentVideoActivity
	                     and not entry.is_video_completed
	                     and entry.seconds_watched > 90),
	            recent_activities)

        max_activities = 3
        return [SuggestedActivity.from_video_activity(va)
                for va in recent_incomplete_videos[0:max_activities]]

    @staticmethod
    def get_goals_for(user_data):
        return []

    @staticmethod
    def get_exercises_for(user_data):
        user_exercise_graph = models.UserExerciseGraph.get(user_data)
        exercise_graph_dicts = user_exercise_graph.suggested_graph_dicts()

        max_activities = 3
        return [SuggestedActivity.from_exercise(d)
                for d in exercise_graph_dicts[0:max_activities]]

    @staticmethod
    def from_exercise(exercise_graph_dict):
        activity = SuggestedActivity()
        activity.name = exercise_graph_dict["display_name"]
        activity.url = models.Exercise.get_relative_url(exercise_graph_dict["name"])
        return activity

    @staticmethod
    def from_video_activity(recent_video_activity):
        activity = SuggestedActivity()
        activity.name = recent_video_activity.video_title
        activity.url = "/video?v=%s" % recent_video_activity.youtube_id
        return activity
