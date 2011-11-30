from badges import BadgeCategory
from topic_badges import TopicBadge
from templatefilters import seconds_to_time_string

# All badges awarded for watching a specific amount of topic video time inherit from TopicVideosTimeBadge
class TopicVideosTimeBadge(TopicBadge):

    def is_satisfied_by(self, *args, **kwargs):
        user_topic_videos = kwargs.get("user_topic_videos", None)

        if user_topic_videos is None:
            return False

        return user_topic_videos.seconds_watched >= self.seconds_required

    def extended_description(self):
        return "Watch %s of video in a single topic" % seconds_to_time_string(self.seconds_required)

class NiceTopicVideosTimeBadge(TopicVideosTimeBadge):
    def __init__(self):
        TopicVideosTimeBadge.__init__(self)
        self.seconds_required = 60 * 15
        self.description = "Nice Listener"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class GreatTopicVideosTimeBadge(TopicVideosTimeBadge):
    def __init__(self):
        TopicVideosTimeBadge.__init__(self)
        self.seconds_required = 60 * 30
        self.description = "Great Listener"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class AwesomeTopicVideosTimeBadge(TopicVideosTimeBadge):
    def __init__(self):
        TopicVideosTimeBadge.__init__(self)
        self.seconds_required = 60 * 60
        self.description = "Awesome Listener"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class RidiculousTopicVideosTimeBadge(TopicVideosTimeBadge):
    def __init__(self):
        TopicVideosTimeBadge.__init__(self)
        self.seconds_required = 60 * 60 * 4
        self.description = "Ridiculous Listener"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

class LudicrousTopicVideosTimeBadge(TopicVideosTimeBadge):
    def __init__(self):
        TopicVideosTimeBadge.__init__(self)
        self.seconds_required = 60 * 60 * 10
        self.description = "Ludicrous Listener"
        self.badge_category = BadgeCategory.PLATINUM
        self.points = 0

