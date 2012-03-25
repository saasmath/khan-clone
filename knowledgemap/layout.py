import models
from badges.util_badges import all_badges_dict
from badges.topic_exercise_badges import TopicExerciseBadge

def topics_layout(user_data):
    """ Return topics layout data with per-user badge completion info
    already filled in.
    """

    # TODO(kamens) STOPSHIP: again, just moving store of this data
    # around so we can see what the map'll look like
    import simplejson as json
    f = open("knowledgemap/layout.json", "r")
    layout = json.loads(f.read())
    f.close()

    layout["polylines"] = []

    # Check for badge completion in each topic
    for topic_dict in layout["topics"]:

        badge_name = TopicExerciseBadge.name_for_topic_key_name(topic_dict["key_name"])
        badge = all_badges_dict().get(badge_name, None)

        if badge and badge.is_already_owned_by(user_data):
            topic_dict["status"] = "proficient"

    return layout
