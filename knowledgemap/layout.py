# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from google.appengine.ext import db

import object_property
import models
from badges.util_badges import all_badges_dict
from badges.topic_exercise_badges import TopicExerciseBadge

def topics_layout(user_data):
    """ Return topics layout data with per-user badge completion info
    already filled in.
    """

    layout = MapLayout.get_for_version(models.TopicVersion.get_default_version()).layout

    if not layout:
        raise Exception("Missing map layout for default topic version")

    layout["polylines"] = []

    # Check for badge completion in each topic
    for topic_dict in layout["topics"]:

        badge_name = TopicExerciseBadge.name_for_topic_key_name(topic_dict["key_name"])
        badge = all_badges_dict().get(badge_name, None)

        if badge and badge.is_already_owned_by(user_data):
            topic_dict["status"] = "proficient"

    return layout

class MapLayout(db.Model):
    """ Keep track of topic layout and polyline paths for knowledge
    map rendering.

    TODO: in the future, this can hold the layout for exercises
    and perhaps all sorts of zones of the knowledge map."""

    version = db.ReferenceProperty(indexed=False, required=True)
    layout = object_property.UnvalidatedObjectProperty()

    @property
    def id(self):
        return self.key().name()

    @staticmethod
    def key_for_version(version):
        return "maplayout:%s" % version.number

    @staticmethod
    def get_for_version(version):
        key = MapLayout.key_for_version(version)
        map_layout = MapLayout.get_by_key_name(key)

        if not map_layout:
            map_layout = MapLayout(
                    key_name = key,
                    version = version,
                    layout = None
            )

        return map_layout
