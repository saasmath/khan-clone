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

NUM_SUGGESTED_TOPICS = 2

def topics_layout(user_data, user_exercise_graph):
    """ Return topics layout data with per-user topic completion 
    and suggested info already filled in.
    """

    layout = MapLayout.get_for_version(models.TopicVersion.get_default_version()).layout

    if not layout:
        raise Exception("Missing map layout for default topic version")

    # TODO: once Eater completes his work, re-enable polyline rendering
    layout["polylines"] = []

    # Build each topic's completion/suggested status from constituent exercises
    for topic_dict in layout["topics"]:

        # We currently use TopicExerciseBadge as the quickest cached list of constituent
        # exercise names in each topic. TODO: once this data is elsewhere, we don't need
        # to use this badge.
        badge_name = TopicExerciseBadge.name_for_topic_key_name(topic_dict["key_name"])
        badge = all_badges_dict().get(badge_name, None)
        if not badge:
            raise Exception("Missing topic badge for topic: %s" % topic_dict["standalone_title"])

        proficient, suggested, total = (0, 0, 0)

        for exercise_name in badge.exercise_names_required:
            graph_dict = user_exercise_graph.graph_dict(exercise_name)

            total += 1
            if graph_dict["proficient"]:
                proficient += 1
            if graph_dict["suggested"]:
                suggested += 1

        # Send down the number of suggested exercises as well as 
        # the ratio of constituent exercises completed:total
        topic_dict["count_suggested"] = suggested
        topic_dict["count_proficient"] = proficient
        topic_dict["total"] = total

        if proficient >= suggested:
            topic_dict["status"] = "proficient"

    # Pick the two "most suggested" topics and highlight them as suggested.
    # "Most suggested" is defined as having the highest number of suggested constituent
    # exercises.
    suggested_candidates = sorted(
            layout["topics"], 
            key=lambda t: t["count_suggested"], 
            reverse=True)[:NUM_SUGGESTED_TOPICS]

    for topic_dict in suggested_candidates:
        topic_dict["suggested"] = True

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
