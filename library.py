import datetime
import os
import logging

import shared_jinja

from app import App
import layer_cache
from models import Video, Setting, Topic
from topics_list import topics_list
import request_handler
import util
import urllib2
import re


@layer_cache.cache(layer=layer_cache.Layers.Memcache | layer_cache.Layers.Datastore, expiration=86400)
def getSmartHistoryContent():
    request = urllib2.Request("http://smarthistory.org/khan-home.html")
    try:
        response = urllib2.urlopen(request)
        smart_history = response.read()
        smart_history = re.search(re.compile("<body>(.*)</body>", re.S), smart_history).group(1).decode("utf-8")
        smart_history.replace("script", "")
    except Exception, e:
        logging.exception("Failed fetching smarthistory video list")
        smart_history = None
        pass
    return smart_history

@layer_cache.cache_with_key_fxn(
        lambda *args, **kwargs: "library_content_by_topic_%s" % Setting.cached_library_content_date()
        )
def library_content_html():
    smart_history = getSmartHistoryContent()
    root = Topic.get_by_readable_id("root").make_tree(types=["Video"])

    topic_prev = None
    for topic in root.children:
        if topic_prev:
            topic_prev.next = topic
        topic_prev = topic

    # Separating out the columns because the formatting is a little different on each column
    template_values = {
        'topic_root': root,
        'smart_history': smart_history,
        }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    # Set shared date of last generated content
    Setting.cached_library_content_date(str(datetime.datetime.now())) 
    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    def get(self, from_task_queue = False):
        library_content_html(bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

