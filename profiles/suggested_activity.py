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
        """ Retrieves a list of suggested "activites" bucketed by type.

            user_data - the student to retrieve suggestions for
            recent_activities - a list of recent activities so that suggestions
                can be based on them.
        """
        return {
            "exercises": SuggestedActivity.get_exercises_for(user_data),
            "videos": SuggestedActivity.get_videos_for(user_data,
                                                       recent_activities),
            "goals": SuggestedActivity.get_goals_for(user_data),
        }

    @staticmethod
    def get_videos_for(user_data, recent_activities):
        recent_completed_ids = set([v.youtube_id for v in filter(
	            lambda entry:
	                    (entry.__class__ == recent_activity.RecentVideoActivity
	                     and entry.is_video_completed),
	            recent_activities)])

        # Note that we can't just look for entries with is_video_completed false
        # since the user may have completed it in a later entry after a break.
        recent_incomplete_videos = filter(
	            lambda entry:
	                    (entry.__class__ == recent_activity.RecentVideoActivity
	                     and entry.youtube_id not in recent_completed_ids
	                     and entry.seconds_watched > 90),
	            recent_activities)

        max_activities = 3
        suggestions = [SuggestedActivity.from_video_activity(va)
                       for va in recent_incomplete_videos[:max_activities]]

        if len(suggestions) < max_activities:
            # STOPSHIP: consolidate this with the call in get_exercises_for
            user_exercise_graph = models.UserExerciseGraph.get(user_data)
            exercise_graph_dicts = user_exercise_graph.suggested_graph_dicts()

            completed = set([
                models.UserVideo.video.get_value_for_datastore(uv)
                for uv in models.UserVideo.get_completed_user_videos(user_data)
            ])
            # STOPSHIP: this results in way too many DB hits - have to figure
            # out a better way to do this before launch.

            # Suggest based on upcoming exercises
            for exercise_dict in exercise_graph_dicts:
                exercise = models.Exercise.get_by_name(exercise_dict['name'])
                for exercise_video in exercise.related_videos_query():
                    if (models.ExerciseVideo.video
                            .get_value_for_datastore(exercise_video)
                            in completed):
                        continue
                    suggestions.append(SuggestedActivity.from_video(
                            exercise_video.video))
                    if len(suggestions) >= max_activities:
                        return suggestions

        return suggestions

    @staticmethod
    def get_goals_for(user_data):
        return []

    @staticmethod
    def get_exercises_for(user_data):
        user_exercise_graph = models.UserExerciseGraph.get(user_data)
        exercise_graph_dicts = user_exercise_graph.suggested_graph_dicts()

        max_activities = 3
        return [SuggestedActivity.from_exercise(d)
                for d in exercise_graph_dicts[:max_activities]]

    @staticmethod
    def from_exercise(exercise_graph_dict):
        activity = SuggestedActivity()
        activity.name = exercise_graph_dict["display_name"]
        activity.url = models.Exercise.get_relative_url(exercise_graph_dict["name"])
        return activity

    @staticmethod
    def from_video_activity(recent_video_activity):
        """ Builds a SuggestedActivity dict from a RecentVideoActivity obect """
        activity = SuggestedActivity()
        activity.name = recent_video_activity.video_title
        activity.url = "/video?v=%s" % recent_video_activity.youtube_id
        return activity

    @staticmethod
    def from_video(video):
        """ Builds a SuggestedActivity dict from a models.Video object """
        activity = SuggestedActivity()
        activity.name = video.title
        activity.url = video.relative_url
        return activity

