import datetime
import logging

import shared_jinja

from app import App
import layer_cache
from models import Video, Setting, Topic, TopicVersion
import request_handler
import util
import urllib2
import re
import math
import time

@layer_cache.cache_with_key_fxn(
        lambda ajax=False, version_number=None: 
        "library_content_by_topic_%s_v%s" % (
        "ajax" if ajax else "inline", 
        version_number if version_number else Setting.topic_tree_version())
        )
def library_content_html(ajax=False, version_number=None):
    """" Returns the HTML for the structure of the topics as they will be
    populated ont he homepage. Does not actually contain the list of video
    names as those are filled in later asynchronously via the cache.
    """
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    topics = Topic.get_filled_content_topics(types = ["Video", "Url"], version=version)

    # special case the duplicate topics for now, eventually we need to either make use of multiple parent functionality (with a hack for a different title), or just wait until we rework homepage
    topics = [topic for topic in topics 
              if not 
              (topic.standalone_title == "California Standards Test: Algebra I" 
              and not topic.id == "algebra-i") and not 
              (topic.standalone_title == "California Standards Test: Geometry" 
              and not topic.id == "geometry-2")] 

    topic_prev = None
    for topic in topics:
        if topic_prev:
            topic_prev.next = topic
        topic_prev = topic

    timestamp = time.time()
    template_values = {
        'topics': topics,
        'ajax' : ajax,
        # convert timestamp to a nice integer for the JS
        'timestamp': int(round(timestamp * 1000))
    }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    def get(self, from_task_queue = False):
        library_content_html(bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

