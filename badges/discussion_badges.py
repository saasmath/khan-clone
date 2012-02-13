from badges import Badge, BadgeCategory

class FirstFlagBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = "Flag Duty"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

    def extended_description(self):
        return "Flag your first question, comment, or answer beneath a video for a moderator's attention"

    def is_manually_awarded(self):
        return True

class FirstUpVoteBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = "Thumbs Up"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

    def extended_description(self):
        return "Cast your first up vote for a helpful question, answer, or comment beneath a video"

    def is_manually_awarded(self):
        return True

class FirstDownVoteBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = "Thumbs Down"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

    def extended_description(self):
        return "Cast your first down vote for an unhelpful question, answer, or comment beneath a video"

    def is_manually_awarded(self):
        return True
