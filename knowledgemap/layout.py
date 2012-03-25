from badges.util_badges import all_badges_dict
from badges.topic_exercise_badges import TopicExerciseBadge

# TODO(kamens): obviously this isn't how we'll store the data --
# just trying to get data format and access patterns down

def topics_layout(user_data):
    """ Return topics layout data with per-user badge completion info
    already filled in.
    """
    layout = topics_layout_skeleton()

    # Check for badge completion in each topic
    for topic_dict in layout["topics"]:

        badge_name = TopicExerciseBadge.name_for_topic_key_name(topic_dict["key_name"])
        badge = all_badges_dict().get(badge_name, None)

        if badge and badge.is_already_owned_by(user_data):
            topic_dict["status"] = "proficient"

    return layout

def topics_layout_skeleton():
    return {
        "topics": [
            {
                "id": "addition-subtraction",
                "key_name": "QFBqv9HZLk_KuLHw4ZKKlg091934jRS9BkNQofEM",
                "standalone_title": "Addition and subtraction",
                "icon_url": "/images/power-mode/badges/addition-and-subtraction-60x60.png",
                "x": 4,
                "y": 3,
            },
            {
                "id": "absolute-value",
                "key_name": "yYz7VOgJHEdSv9uC3cuwb8kOf-k5sL9VlfBCfoVO",
                "standalone_title": "Absolute value",
                "icon_url": "/images/power-mode/badges/default-60x60.png",
                "x": 8,
                "y": 5,
            },
            {
                "id": "multiplication-division",
                "key_name": "ZzoKc5tUA9UqBsrOHxHmTo22VVnALOf9YdN4xK_B",
                "standalone_title": "Multiplication and division",
                "icon_url": "/images/power-mode/badges/multiplication-and-division-60x60.png",
                "x": 0,
                "y": 5,
            },
        ],

        "polylines": [
            {
                "path": [
                    { "x": 4, "y": 3 },
                    { "x": 8, "y": 4 },
                    { "x": 8, "y": 5 },
                ],
            },
            {
                "path": [
                    { "x": 4, "y": 3 },
                    { "x": 0, "y": 4 },
                    { "x": 0, "y": 5 },
                ],
            },
        ]
    }
