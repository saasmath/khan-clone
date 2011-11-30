from badges import Badge, BadgeContextType

# All badges that may be awarded once-per-Topic inherit from TopicBadge
class TopicBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.badge_context_type = BadgeContextType.TOPIC

    def is_already_owned_by(self, user_data, *args, **kwargs):
        user_topic_videos = kwargs.get("user_topic_videos", None)
        if user_topic_videos is None:
            return False

        return self.name_with_target_context(user_topic_videos.title) in user_data.badges

    def award_to(self, user_data, *args, **kwargs):
        user_topic_videos = kwargs.get("user_topic_videos", None)
        if user_topic_videos is None:
            return False

        self.complete_award_to(user_data, user_topic_videos.topic, user_topic_videos.topic.title)

