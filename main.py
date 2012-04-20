#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
import logging
import re
# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import urlfetch

import webapp2
from webapp2_extras.routes import DomainRoute
from webapp2_extras.routes import RedirectRoute

# It's important to have this prior to the imports below that require imports
# to request_handler.py. The structure of the imports are such that this
# module causes a lot of circular imports to happen, so including it once out
# the way at first seems to fix some of those issues.
import templatetags #@UnusedImport

import devpanel
import bulk_update.handler
import request_cache
from gae_mini_profiler import profiler
from gae_bingo.middleware import GAEBingoWSGIMiddleware
import autocomplete
import coaches
import knowledgemap.handlers
import youtube_sync
import warmup
import library
import login
import homepage

import search

import request_handler
from app import App
import util
import user_util
import exercise_statistics
import activity_summary
import dashboard.handlers
import exercises.exercise_util
import exercises.handlers
import exercisestats.report
import exercisestats.report_json
import exercisestats.exercisestats_util
import gandalf
import github
import paypal
import smarthistory
import topics
import goals.handlers
import appengine_stats
import stories
import summer
import common_core
import unisubs
import api.jsonify
import socrates
import labs.explorations
import layer_cache
import kmap_editor

import topic_models
import video_models
import user_models
from user_models import UserData
from video_models import Video
from url_model import Url
from exercise_video_model import ExerciseVideo
from topic_models import Topic
from discussion import comments, notification, qa, voting, moderation
from about import blog, util_about
from coach_resources import util_coach, schools_blog
from phantom_users import util_notify
from badges import util_badges, custom_badges
from mailing_lists import util_mailing_lists
from profiles import util_profile
from custom_exceptions import MissingVideoException, PageNotFoundException
from oauth_provider import apps as oauth_apps
from phantom_users.cloner import Clone
from image_cache import ImageCache
from api.auth.xsrf import ensure_xsrf_cookie
import redirects
import robots
from importer.handlers import ImportHandler

from gae_bingo.gae_bingo import bingo, ab_test

class VideoDataTest(request_handler.RequestHandler):

    @user_util.developer_required
    def get(self):
        self.response.out.write('<html>')
        videos = Video.all()
        for video in videos:
            self.response.out.write('<P>Title: ' + video.title)

class TopicPage(request_handler.RequestHandler):

    @staticmethod
    def show_topic(handler, topic):
        selected_topic = topic
        parent_topic = db.get(topic.parent_keys[0])

        # If the parent is a supertopic, use that instead
        if parent_topic.id in Topic._super_topic_ids:
            topic = parent_topic
        elif not (topic.id in Topic._super_topic_ids or
                  topic.has_children_of_type(["Video"])):
            handler.redirect("/", True)
            return

        template_values = {
            "main_topic": topic,
            "selected_topic": selected_topic,
        }
        handler.render_jinja2_template('viewtopic.html', template_values)

    @user_util.open_access
    @ensure_xsrf_cookie
    def get(self, path):
        """ Display a topic page if the URL matches a pre-existing topic,
        such as /math/algebra or /algebra
        
        NOTE: Since there is no specific route we are matching,
        this handler is registered as the default handler, 
        so unrecognized paths will return a 404.
        """
        if path.endswith('/'):
            # Canonical paths do not have trailing slashes
            path = path[:-1]

        path_list = path.split('/')
        if len(path_list) > 0:
            # Only look at the actual topic ID
            topic = topic_models.Topic.get_by_id(path_list[-1])

            if topic:
                bingo("topic_pages_view_page")
                # End topic pages A/B test

                if path != topic.get_extended_slug():
                    # If the topic ID is found but the path is incorrect,
                    # redirect the user to the canonical path
                    self.redirect("/%s" % topic.get_extended_slug(), True)
                    return

                TopicPage.show_topic(self, topic)
                return

        # error(404) sets the status code to 404. Be aware that execution continues
        # after the .error call.
        self.error(404)
        raise PageNotFoundException("Page not found")
    

# New video view handler.
# The URI format is a topic path followed by /v/ and then the video identifier, i.e.:
#   /math/algebra/introduction-to-algebra/v/origins-of-algebra
class ViewVideo(request_handler.RequestHandler):

    @staticmethod
    def show_video(handler, readable_id, topic_id,
                   redirect_to_canonical_url=False):
        topic = None
        query_string = ''

        if topic_id is not None and len(topic_id) > 0:
            topic = Topic.get_by_id(topic_id)
            key_id = 0 if not topic else topic.key().id()

        # If a topic_id wasn't specified or the specified topic wasn't found
        # use the first topic for the requested video.
        if topic is None:
            # Get video by readable_id to get the first topic for the video
            video = Video.get_for_readable_id(readable_id)
            if video is None:
                raise MissingVideoException("Missing video '%s'" %
                                            readable_id)

            topic = video.first_topic()
            if not topic:
                raise MissingVideoException("No topic has video '%s'" %
                                            readable_id)

            if handler.request.query_string:
                query_string = '?' + handler.request.query_string

            redirect_to_canonical_url = True


        if redirect_to_canonical_url:
            url = "/%s/v/%s%s" % (topic.get_extended_slug(),
                                  urllib.quote(readable_id),
                                  query_string)
            logging.info("Redirecting to %s" % url)
            handler.redirect(url, True)
            return None

        # Note: Bingo conversions are tracked on the client now,
        # so they have been removed here. (tomyedwab)

        topic_data = topic.get_play_data()

        discussion_options = qa.add_template_values({}, handler.request)
        video_data = Video.get_play_data(readable_id, topic,
                                         discussion_options)
        if video_data is None:
            raise MissingVideoException("Missing video '%s'" % readable_id)

        template_values = {
            "topic_data": topic_data,
            "topic_data_json": api.jsonify.jsonify(topic_data),
            "video": video_data,
            "video_data_json": api.jsonify.jsonify(video_data),
            "selected_nav_link": 'watch',
        }

        return template_values

    @user_util.open_access
    @ensure_xsrf_cookie
    def get(self, path, video_id):
        if path:
            path_list = path.split('/')

            if len(path_list) > 0:
                topic_id = path_list[-1]
                template_values = ViewVideo.show_video(self, video_id, topic_id)
                if template_values:
                    self.render_jinja2_template('viewvideo.html', template_values)

class ViewVideoDeprecated(request_handler.RequestHandler):

    # The handler itself is deprecated. The ViewVideo handler is the canonical
    # handler now.
    @user_util.open_access
    @ensure_xsrf_cookie
    def get(self, readable_id=""):
        # This method displays a video in the context of a particular topic.
        # To do that we first need to find the appropriate topic.  If we aren't
        # given the topic title in a query param, we need to find a topic that
        # the video is a part of.  That requires finding the video, given it readable_id
        # or, to support old URLs, it's youtube_id.
        video = None
        video_id = self.request.get('v')
        topic_id = self.request_string('topic', default="")
        readable_id = urllib.unquote(readable_id)
        readable_id = re.sub('-+$', '', readable_id)  # remove any trailing dashes (see issue 1140)

        # If either the readable_id or topic title is missing,
        # redirect to the canonical URL that contains them
        if video_id: # Support for old links
            query = Video.all()
            query.filter('youtube_id =', video_id)
            video = query.get()

            if not video:
                raise MissingVideoException("Missing video w/ youtube id '%s'" % video_id)

            readable_id = video.readable_id
            topic = video.first_topic()

            if not topic:
                raise MissingVideoException("No topic has video w/ youtube id '%s'" % video_id)

        ViewVideo.show_video(self, readable_id, topic_id, True)

class ReportIssue(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):
        issue_type = self.request.get('type')
        self.write_response(issue_type, {'issue_labels': self.request.get('issue_labels'), })

    def write_response(self, issue_type, extra_template_values):
        user_agent = self.request.headers.get('User-Agent')
        if user_agent is None:
            user_agent = ''
        user_agent = user_agent.replace(',', ';') # Commas delimit labels, so we don't want them
        template_values = {
            'referer': self.request.headers.get('Referer'),
            'user_agent': user_agent,
            }
        template_values.update(extra_template_values)
        page = 'reportissue_template.html'
        if issue_type == 'Defect':
            page = 'reportproblem.html'
        elif issue_type == 'Enhancement':
            page = 'makesuggestion.html'
        elif issue_type == 'New-Video':
            page = 'requestvideo.html'
        elif issue_type == 'Comment':
            page = 'makecomment.html'
        elif issue_type == 'Question':
            page = 'askquestion.html'

        self.render_jinja2_template(page, template_values)

class Crash(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        if self.request_bool("capability_disabled", default=False):
            raise CapabilityDisabledError("Simulate scheduled GAE downtime")
        else:
            # Even Watson isn't perfect
            raise Exception("What is Toronto?")

# TODO(csilvers): unused: remove
class ReadOnlyDowntime(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        raise CapabilityDisabledError("App Engine maintenance period")

    @user_util.open_access
    def post(self):
        return self.get()

class SendToLog(request_handler.RequestHandler):
    @user_util.open_access
    def post(self):
        message = self.request_string("message", default="")
        if message:
            logging.critical("Manually sent to log: %s" % message)

class MobileFullSite(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.set_mobile_full_site_cookie(True)
        self.redirect("/")

class MobileSite(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.set_mobile_full_site_cookie(False)
        self.redirect("/")

class ViewContribute(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('contribute.html', {"selected_nav_link": "contribute"})

class ViewCredits(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('viewcredits.html', {"selected_nav_link": "contribute"})

class Donate(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('donate.html', {"selected_nav_link": "donate"})

class ViewTOS(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('tos.html', {"selected_nav_link": "tos"})

class ViewAPITOS(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('api-tos.html', {"selected_nav_link": "api-tos"})

class ViewPrivacyPolicy(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('privacy-policy.html', {"selected_nav_link": "privacy-policy"})

class ViewDMCA(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('dmca.html', {"selected_nav_link": "dmca"})

class RetargetFeedback(bulk_update.handler.UpdateKind):
    def get_keys_query(self, kind):
        """Returns a keys-only query to get the keys of the entities to update"""
        return db.GqlQuery('select __key__ from Feedback')

    def use_transaction(self):
        return False

    def update(self, feedback):
        orig_video = feedback.video()

        if orig_video == None or type(orig_video).__name__ != "Video":
            return False
        readable_id = orig_video.readable_id
        query = Video.all()
        query.filter('readable_id =', readable_id)
        # The database currently contains multiple Video objects for a particular
        # video.  Some are old.  Some are due to a YouTube sync where the youtube urls
        # changed and our code was producing youtube_ids that ended with '_player'.
        # This hack gets the most recent valid Video object.
        key_id = 0
        for v in query:
            if v.key().id() > key_id and not v.youtube_id.endswith('_player'):
                video = v
                key_id = v.key().id()
        # End of hack
        if video is not None and video.key() != orig_video.key():
            logging.info("Retargeting Feedback %s from Video %s to Video %s", feedback.key().id(), orig_video.key().id(), video.key().id())
            feedback.targets[0] = video.key()
            return True
        else:
            return False

class ChangeEmail(bulk_update.handler.UpdateKind):

    def get_email_params(self):
        old_email = self.request.get('old')
        new_email = self.request.get('new')
        prop = self.request.get('prop')
        if old_email is None or len(old_email) == 0:
            raise Exception("parameter 'old' is required")
        if new_email is None or len(new_email) == 0:
            new_email = old_email
        if prop is None or len(prop) == 0:
            prop = "user"
        return (old_email, new_email, prop)

    @user_util.admin_required
    def get(self):
        (old_email, new_email, prop) = self.get_email_params()
        if new_email == old_email:
            return bulk_update.handler.UpdateKind.get(self)
        # TODO(csilvers): take this out once admin-only does
        # XSRF-checking everywhere?
        self.response.out.write("To prevent a CSRF attack from changing email addresses, you initiate an email address change from the browser. ")
        self.response.out.write("Instead, run the following from remote_api_shell.py.<pre>\n")
        self.response.out.write("import bulk_update.handler\n")
        self.response.out.write("bulk_update.handler.start_task('%s',{'kind':'%s', 'old':'%s', 'new':'%s'})\n"
                                % (self.request.path, self.request.get('kind'), old_email, new_email))
        self.response.out.write("</pre>and then check the logs in the admin console")


    def get_keys_query(self, kind):
        """Returns a keys-only query to get the keys of the entities to update"""

        (old_email, new_email, prop) = self.get_email_params()
        # When a user's personal Google account is replaced by their transitioned Google Apps account with the same email,
        # the Google user ID changes and the new User object's are not considered equal to the old User object's with the same
        # email, so querying the datastore for entities referring to users with the same email return nothing. However an inequality
        # query will return the relevant entities.
        gt_user = users.User(old_email[:-1] + chr(ord(old_email[-1]) - 1) + chr(127))
        lt_user = users.User(old_email + chr(0))
        return db.GqlQuery(('select __key__ from %s where %s > :1 and %s < :2' % (kind, prop, prop)), gt_user, lt_user)

    def use_transaction(self):
        return False

    def update(self, entity):
        (old_email, new_email, prop) = self.get_email_params()
        if getattr(entity, prop).email() != old_email:
            # This should never occur, but just in case, don't change or reput the entity.
            return False
        setattr(entity, prop, users.User(new_email))
        return True

class Search(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):
        if not gandalf.gandalf("new_faster_search"):
            self.get_old()
            return

        query = self.request.get('page_search_query')
        template_values = {'page_search_query': query}
        query = query.strip()
        if len(query) < search.SEARCH_PHRASE_MIN_LENGTH:
            if len(query) > 0:
                template_values.update({
                    'query_too_short': search.SEARCH_PHRASE_MIN_LENGTH
                })
            self.render_jinja2_template("searchresults_new.html", template_values)
            return
        searched_phrases = []

        url = "http://search-rpc.khanacademy.org/solr/select/?q=version%%3A1+%%2B%s&start=0&rows=9999&indent=on&wt=json&fl=*%%20score" % urllib.quote(query)
        try:
            logging.info("Fetching: %s" % url)
            response = urlfetch.fetch(url = url, deadline=25)
            response_object = json.loads(response.content)
        except Exception, e:
            logging.error("Failed to fetch search results from search-rpc!")
            template_values.update({
                'server_timout': True
            })
            self.render_jinja2_template("searchresults_new.html", template_values)
            return

        logging.info("Received response: %d" % response_object["response"]["numFound"])

        matching_topics = [t for t in response_object["response"]["docs"] if t["kind"] == "Topic"]
        if matching_topics:
            matching_topic_count = 1
            matching_topic = matching_topics[0] if matching_topics else None
            matching_topic["children"] = json.loads(matching_topic["child_topics"]) if "child_topics" in matching_topic else None
        else:
            matching_topic_count = 0
            matching_topic = None

        videos = [v for v in response_object["response"]["docs"] if v["kind"] == "Video"]
        topics = {}

        for video in videos:
            video["related_exercises"] = json.loads(video["related_exercises"])

            parent_topic = json.loads(video["parent_topic"])
            topic_id = parent_topic["id"]
            if topic_id not in topics:
                topics[topic_id] = parent_topic
                topics[topic_id]["videos"] = []
                topics[topic_id]["match_count"] = 0

            topics[topic_id]["videos"].append(video)
            topics[topic_id]["match_count"] += 1

        topics_list = sorted(topics.values(), key=lambda topic: -topic["match_count"])

        template_values.update({
                           'topics': topics_list,
                           'matching_topic': matching_topic,
                           'videos': videos,
                           'search_string': query,
                           'video_count': len(videos),
                           'topic_count': len(topics_list),
                           'matching_topic_count': matching_topic_count
                           })

        self.render_jinja2_template("searchresults_new.html", template_values)

    @user_util.admin_required
    def update(self):
        if App.is_dev_server:
            new_version = topic_models.TopicVersion.get_default_version()
            old_version_number = layer_cache.KeyValueCache.get(
                "last_dev_topic_vesion_indexed")
            
            # no need to update if current version matches old version
            if new_version.number == old_version_number:
                return False

            if old_version_number:
                old_version = topic_models.TopicVersion.get_by_id(
                                                            old_version_number)
            else:
                old_version = None

            topic_models.rebuild_search_index(new_version, old_version)
    
            layer_cache.KeyValueCache.set("last_dev_topic_vesion_indexed", 
                                          new_version.number)

    def get_old(self):
        """ Deprecated old version of search, so we can Gandalf in the new one.

        Will eventually disappear.
        """

        show_update = False
        if App.is_dev_server and user_util.is_current_user_admin():
            update = self.request_bool("update", False)
            if update:
                self.update()

            version_number = layer_cache.KeyValueCache.get(
                "last_dev_topic_vesion_indexed")
            default_version = topic_models.TopicVersion.get_default_version()
            if version_number != default_version.number:
                show_update = True

        query = self.request.get('page_search_query')
        template_values = {'page_search_query': query}
        query = query.strip()
        if len(query) < search.SEARCH_PHRASE_MIN_LENGTH:
            if len(query) > 0:
                template_values.update({
                    'query_too_short': search.SEARCH_PHRASE_MIN_LENGTH
                })
            self.render_jinja2_template("searchresults.html", template_values)
            return
        searched_phrases = []

        # Do an async query for all ExerciseVideos, since this may be slow
        exvids_query = ExerciseVideo.all()
        exvids_future = util.async_queries([exvids_query])

        # One full (non-partial) search, then sort by kind
        all_text_keys = Topic.full_text_search(
                query, limit=50, kind=None,
                stemming=Topic.INDEX_STEMMING,
                multi_word_literal=Topic.INDEX_MULTI_WORD,
                searched_phrases_out=searched_phrases)

        # Quick title-only partial search
        topic_partial_results = filter(
                lambda topic_dict: query in topic_dict["title"].lower(),
                autocomplete.topic_title_dicts())
        video_partial_results = filter(
                lambda video_dict: query in video_dict["title"].lower(),
                autocomplete.video_title_dicts())
        url_partial_results = filter(
                lambda url_dict: query in url_dict["title"].lower(),
                autocomplete.url_title_dicts())

        # Combine results & do one big get!
        all_key_list = [str(key_and_title[0]) for key_and_title in all_text_keys]
        all_key_list.extend([result["key"] for result in topic_partial_results])
        all_key_list.extend([result["key"] for result in video_partial_results])
        all_key_list.extend([result["key"] for result in url_partial_results])
        all_key_list = list(set(all_key_list))

        # Filter out anything that isn't a Topic, Url or Video
        all_key_list = [key for key in all_key_list if db.Key(key).kind() in ["Topic", "Url", "Video"]]

        # Get all the entities
        all_entities = db.get(all_key_list)

        # Group results by type
        topics = []
        videos = []
        for entity in all_entities:
            if isinstance(entity, Topic):
                topics.append(entity)
            elif isinstance(entity, Video):
                videos.append(entity)
            elif isinstance(entity, Url):
                videos.append(entity)
            elif entity:
                logging.info("Found unknown object " + repr(entity))

        # Get topics for videos not in matching topics
        filtered_videos = []
        filtered_videos_by_key = {}
        for video in videos:
            if [(str(topic.key()) in video.topic_string_keys) for topic in topics].count(True) == 0:
                video_topic = video.first_topic()
                if video_topic != None:
                    topics.append(video_topic)
                    filtered_videos.append(video)
                    filtered_videos_by_key[str(video.key())] = []
            else:
                filtered_videos.append(video)
                filtered_videos_by_key[str(video.key())] = []
        video_count = len(filtered_videos)

        # Get the related exercises
        all_exercise_videos = exvids_future[0].get_result()
        exercise_keys = []
        for exvid in all_exercise_videos:
            video_key = str(ExerciseVideo.video.get_value_for_datastore(exvid))
            if video_key in filtered_videos_by_key:
                exercise_key = ExerciseVideo.exercise.get_value_for_datastore(exvid)
                video_exercise_keys = filtered_videos_by_key[video_key]
                video_exercise_keys.append(exercise_key)
                exercise_keys.append(exercise_key)
        exercises = db.get(exercise_keys)

        # Sort exercises with videos
        video_exercises = {}
        for video_key, exercise_keys in filtered_videos_by_key.iteritems():
            video_exercises[video_key] = map(lambda exkey: [exercise for exercise in exercises if exercise.key() == exkey][0], exercise_keys)

        # Count number of videos in each topic and sort descending
        topic_count = 0
        matching_topic_count = 0
        if topics:
            if len(filtered_videos) > 0:
                for topic in topics:
                    topic.match_count = [(str(topic.key()) in video.topic_string_keys) for video in filtered_videos].count(True)
                    if topic.match_count > 0:
                        topic_count += 1

                topics = sorted(topics, key=lambda topic:-topic.match_count)
            else:
                for topic in topics:
                    topic.match_count = 0

            for topic in topics:
                if topic.title.lower() == query:
                    topic.matches = True
                    matching_topic_count += 1

                    child_topics = topic.get_child_topics(include_descendants=True)
                    topic.child_topics = [t for t in child_topics if t.has_content()]

        template_values.update({
                           'show_update': show_update,
                           'topics': topics,
                           'videos': filtered_videos,
                           'video_exercises': video_exercises,
                           'search_string': query,
                           'video_count': video_count,
                           'topic_count': topic_count,
                           'matching_topic_count': matching_topic_count
                           })

        self.render_jinja2_template("searchresults.html", template_values)

class PermanentRedirectToHome(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):

        redirect_target = "/"
        relative_path = self.request.path.rpartition('/')[2].lower()

        # Permanently redirect old JSP version of the site to home
        # or, in the case of some special targets, to their appropriate new URL
        dict_redirects = {
            "sat.jsp": "/sat",
            "gmat.jsp": "/gmat",
        }

        if dict_redirects.has_key(relative_path):
            redirect_target = dict_redirects[relative_path]

        self.redirect(redirect_target, True)

class ServeUserVideoCss(request_handler.RequestHandler):
    @user_util.login_required
    def get(self):
        user_data = UserData.current()
        user_video_css = video_models.UserVideoCss.get_for_user_data(user_data)
        self.response.headers['Content-Type'] = 'text/css'

        if user_video_css.version == user_data.uservideocss_version:
            # Don't cache if there's a version mismatch and update isn't finished
            self.response.headers['Cache-Control'] = 'public,max-age=1000000'

        self.response.out.write(user_video_css.video_css)

class MemcacheViewer(request_handler.RequestHandler):
    @user_util.developer_required
    def get(self):
        key = self.request_string("key", "__layer_cache_models._get_settings_dict__")
        namespace = self.request_string("namespace", App.version)
        values = memcache.get(key, namespace=namespace)
        self.response.out.write("Memcache key %s = %s.<br>\n" % (key, values))
        if type(values) is dict:
            for k, value in values.iteritems():
                self.response.out.write("<p><b>%s</b>%s</p>" % (k, dict((key, getattr(value, key)) for key in dir(value))))
        if self.request_bool("clear", False):
            memcache.delete(key, namespace=namespace)


application = webapp2.WSGIApplication([
    DomainRoute('smarthistory.khanacademy.org', [
        webapp2.SimpleRoute('/.*', smarthistory.SmartHistoryProxy)
    ]),
    ('/', homepage.ViewHomePage),
    ('/about', util_about.ViewAbout),
    ('/about/blog', blog.ViewBlog),
    RedirectRoute('/about/blog/schools',
        redirect_to='http://ka-implementations.tumblr.com/',
        defaults={'_permanent': False}),
    ('/about/blog/.*', blog.ViewBlogPost),
    ('/about/the-team', util_about.ViewAboutTheTeam),
    ('/about/getting-started', util_about.ViewGettingStarted),
    ('/about/discovery-lab', util_about.ViewDiscoveryLab),
    ('/about/tos', ViewTOS),
    ('/about/api-tos', ViewAPITOS),
    ('/about/privacy-policy', ViewPrivacyPolicy),
    ('/about/dmca', ViewDMCA),
    ('/contribute', ViewContribute),
    RedirectRoute('/getinvolved', redirect_to='/contribute'),
    ('/contribute/credits', ViewCredits),
    ('/frequently-asked-questions', util_about.ViewFAQ),
    ('/about/faq', util_about.ViewFAQ),
    ('/downloads', util_about.ViewDownloads),
    ('/about/downloads', util_about.ViewDownloads),
    ('/donate', Donate),
    ('/exercisedashboard', knowledgemap.handlers.ViewKnowledgeMap),

    ('/stories/submit', stories.SubmitStory),
    ('/stories/?.*', stories.ViewStories),

    # Labs
    ('/labs', labs.LabsRequestHandler),

    ('/labs/explorations', labs.explorations.RequestHandler),
    ('/labs/explorations/([^/]+)', labs.explorations.RequestHandler),
    ('/labs/socrates', socrates.SocratesIndexHandler),
    ('/labs/socrates/(.*)/v/([^/]*)', socrates.SocratesHandler),

    # Issues a command to re-generate the library content.
    ('/library_content', library.GenerateLibraryContent),

    ('/(.*)/e', exercises.handlers.ViewExercise),
    ('/(.*)/e/([^/]*)', exercises.handlers.ViewExercise),
    ('/exercise/(.+)', exercises.handlers.ViewExerciseDeprecated), # /exercise/addition_1
    ('/topicexercise/(.+)', exercises.handlers.ViewTopicExerciseDeprecated), # /topicexercise/addition_and_subtraction
    ('/exercises', exercises.handlers.ViewExerciseDeprecated), # /exercises?exid=addition_1
    ('/(review)', exercises.handlers.ViewExercise),

    ('/khan-exercises/exercises/.*', exercises.exercise_util.RawExercise),
    ('/viewexercisesonmap', knowledgemap.handlers.ViewKnowledgeMap),
    ('/video/(.*)', ViewVideoDeprecated), # Backwards URL compatibility
    ('/v/(.*)', ViewVideoDeprecated), # Backwards URL compatibility
    ('/video', ViewVideoDeprecated), # Backwards URL compatibility
    ('/(.*)/v/([^/]*)', ViewVideo),
    ('/reportissue', ReportIssue),
    ('/search', Search),
    ('/savemapcoords', knowledgemap.handlers.SaveMapCoords),
    ('/crash', Crash),

    ('/image_cache/(.+)', ImageCache),

    ('/mobilefullsite', MobileFullSite),
    ('/mobilesite', MobileSite),

    ('/admin/import_smarthistory', topics.ImportSmartHistory),
    ('/admin/reput', bulk_update.handler.UpdateKind),
    ('/admin/retargetfeedback', RetargetFeedback),
    ('/admin/startnewbadgemapreduce', util_badges.StartNewBadgeMapReduce),
    ('/admin/badgestatistics', util_badges.BadgeStatistics),
    ('/admin/startnewexercisestatisticsmapreduce', exercise_statistics.StartNewExerciseStatisticsMapReduce),
    ('/admin/startnewvotemapreduce', voting.StartNewVoteMapReduce),
    ('/admin/feedbackflagupdate', qa.StartNewFlagUpdateMapReduce),
    ('/admin/dailyactivitylog', activity_summary.StartNewDailyActivityLogMapReduce),
    ('/admin/youtubesync.*', youtube_sync.YouTubeSync),
    ('/admin/changeemail', ChangeEmail),
    ('/admin/unisubs', unisubs.ReportHandler),
    ('/admin/unisubs/import', unisubs.ImportHandler),

    ('/devadmin', devpanel.Panel),
    ('/devadmin/maplayout', kmap_editor.MapLayoutEditor),
    ('/devadmin/emailchange', devpanel.MergeUsers),
    ('/devadmin/managedevs', devpanel.Manage),
    ('/devadmin/managecoworkers', devpanel.ManageCoworkers),
    ('/devadmin/managecommoncore', devpanel.ManageCommonCore),
    ('/commoncore', common_core.CommonCore),
    ('/staging/commoncore', common_core.CommonCore),
    ('/devadmin/content', topics.EditContent),
    ('/devadmin/memcacheviewer', MemcacheViewer),

    # Manually refresh the content caches
    ('/devadmin/refresh', topics.RefreshCaches),

    ('/coach/resources', util_coach.ViewCoachResources),
    ('/coach/demo', util_coach.ViewDemo),
    ('/coach/accessdemo', util_coach.AccessDemo),
    ('/coach/schools-blog', schools_blog.ViewBlog),
    ('/toolkit', util_coach.ViewToolkit),
    ('/toolkit/(.*)', util_coach.ViewToolkit),
    ('/coaches', coaches.ViewCoaches),
    ('/coaches', coaches.ViewCoaches),
    ('/students', coaches.ViewStudents),
    ('/unregisterstudent', coaches.UnregisterStudent),
    ('/requeststudent', coaches.RequestStudent),
    ('/acceptcoach', coaches.AcceptCoach),

    ('/removestudentfromlist', coaches.RemoveStudentFromList),
    ('/addstudenttolist', coaches.AddStudentToList),

    ('/mailing-lists/subscribe', util_mailing_lists.Subscribe),

    ('/profile/graph/activity', util_profile.ActivityGraph),
    ('/profile/graph/focus', util_profile.FocusGraph),
    ('/profile/graph/exercisesovertime', util_profile.ExercisesOverTimeGraph),
    ('/profile/graph/exerciseproblems', util_profile.ExerciseProblemsGraph),


    ('/profile/graph/classexercisesovertime', util_profile.ClassExercisesOverTimeGraph),
    ('/profile/graph/classenergypointsperminute', util_profile.ClassEnergyPointsPerMinuteGraph),
    ('/profile/graph/classtime', util_profile.ClassTimeGraph),
    ('/profile/(.+?)/(.*)', util_profile.ViewProfile),
    ('/profile/(.*)', util_profile.ViewProfile),
    ('/profile', util_profile.ViewProfile),
    ('/class_profile', util_profile.ViewClassProfile),

    ('/login', login.Login),
    ('/login/mobileoauth', login.MobileOAuthLogin),
    ('/postlogin', login.PostLogin),
    ('/logout', login.Logout),
    ('/signup', login.Signup),
    ('/completesignup', login.CompleteSignup),
    ('/pwchange', login.PasswordChange),
    ('/forgotpw', login.ForgotPassword),  # Start of pw-recovery flow
    ('/pwreset', login.PasswordReset),  # For after user clicks on email link

    ('/api-apps/register', oauth_apps.Register),

    # Below are all discussion related pages
    ('/discussion/addcomment', comments.AddComment),
    ('/discussion/pagecomments', comments.PageComments),

    ('/discussion/addquestion', qa.AddQuestion),
    ('/discussion/expandquestion', qa.ExpandQuestion),
    ('/discussion/addanswer', qa.AddAnswer),
    ('/discussion/editentity', qa.EditEntity),
    ('/discussion/answers', qa.Answers),
    ('/discussion/pagequestions', qa.PageQuestions),
    ('/discussion/clearflags', qa.ClearFlags),
    ('/discussion/flagentity', qa.FlagEntity),
    ('/discussion/voteentity', voting.VoteEntity),
    ('/discussion/updateqasort', voting.UpdateQASort),
    ('/admin/discussion/finishvoteentity', voting.FinishVoteEntity),
    ('/discussion/deleteentity', qa.DeleteEntity),
    ('/discussion/changeentitytype', qa.ChangeEntityType),

    ('/discussion/mod', moderation.ModPanel),
    ('/discussion/mod/flaggedfeedback', moderation.FlaggedFeedback),
    ('/discussion/mod/moderatorlist', moderation.ModeratorList),
    ('/discussion/mod/bannedlist', moderation.BannedList),
    RedirectRoute('/discussion/moderatorlist', redirect_to='/discussion/mod'),
    RedirectRoute('/discussion/flaggedfeedback', redirect_to='/discussion/mod'),

    ('/githubpost', github.NewPost),
    ('/githubcomment', github.NewComment),

    ('/paypal/autoreturn', paypal.AutoReturn),
    ('/paypal/ipn', paypal.IPN),

    ('/badges/view', util_badges.ViewBadges),
    ('/badges/custom/create', custom_badges.CreateCustomBadge),
    ('/badges/custom/award', custom_badges.AwardCustomBadge),

    ('/notifierclose', util_notify.ToggleNotify),
    ('/newaccount', Clone),

    ('/dashboard', dashboard.handlers.Dashboard),
    ('/contentdash', dashboard.handlers.ContentDashboard),
    ('/admin/dashboard/record_statistics', dashboard.handlers.RecordStatistics),
    ('/admin/entitycounts', dashboard.handlers.EntityCounts),
    ('/devadmin/contentcounts', dashboard.handlers.ContentCountsCSV),

    ('/sendtolog', SendToLog),

    ('/user_video_css', ServeUserVideoCss),

    ('/admin/exercisestats/collectfancyexercisestatistics', exercisestats.exercisestats_util.CollectFancyExerciseStatistics),
    ('/exercisestats/report', exercisestats.report.Test),
    ('/exercisestats/exerciseovertime', exercisestats.report_json.ExerciseOverTimeGraph),
    ('/exercisestats/geckoboardexerciseredirect', exercisestats.report_json.GeckoboardExerciseRedirect),
    ('/exercisestats/exercisestatsmap', exercisestats.report_json.ExerciseStatsMapGraph),
    ('/exercisestats/exerciseslastauthorcounter', exercisestats.report_json.ExercisesLastAuthorCounter),
    ('/exercisestats/exercisenumbertrivia', exercisestats.report_json.ExerciseNumberTrivia),
    ('/exercisestats/userlocationsmap', exercisestats.report_json.UserLocationsMap),
    ('/exercisestats/exercisescreatedhistogram', exercisestats.report_json.ExercisesCreatedHistogram),

    ('/goals/new', goals.handlers.CreateNewGoal),
    ('/goals/admincreaterandom', goals.handlers.CreateRandomGoalData),

    # Summer Discovery Camp application/registration
    ('/summer/application', summer.Application),
    ('/summer/tuition', summer.Tuition),
    ('/summer/application-status', summer.Status),
    ('/summer/getstudent', summer.GetStudent),
    ('/summer/paypal-autoreturn', summer.PaypalAutoReturn),
    ('/summer/paypal-ipn', summer.PaypalIPN),
    ('/summer/admin/download', summer.Download),
    ('/summer/admin/updatestudentstatus', summer.UpdateStudentStatus),

    # Stats about appengine
    ('/stats/dashboard', dashboard.handlers.Dashboard),
    ('/stats/contentdash', dashboard.handlers.ContentDashboard),
    ('/stats/memcache', appengine_stats.MemcacheStatus),

    ('/robots.txt', robots.RobotsTxt),

    # Hard-coded redirects
    RedirectRoute('/shop', 
            redirect_to='http://khanacademy.myshopify.com',
            defaults={'_permanent': False}),
    RedirectRoute('/jobs<:/?.*>', 
            redirect_to='http://hire.jobvite.com/CompanyJobs/Careers.aspx?k=JobListing&c=qd69Vfw7',
            defaults={'_permanent': False}),
    RedirectRoute('/jobs/<:.*>', 
            redirect_to='http://hire.jobvite.com/CompanyJobs/Careers.aspx?k=JobListing&c=qd69Vfw7',
            defaults={'_permanent': False}),

    # Dynamic redirects are prefixed w/ "/r/" and managed by "/redirects"
    ('/r/.*', redirects.Redirect),
    ('/redirects', redirects.List),
    ('/redirects/add', redirects.Add),
    ('/redirects/remove', redirects.Remove),

    ('/importer', ImportHandler),

    # Redirect any links to old JSP version
    ('/.*\.jsp', PermanentRedirectToHome),
    ('/index\.html', PermanentRedirectToHome),

    ('/_ah/warmup.*', warmup.Warmup),

    # Topic paths can be anything, so we match everything.
    # The TopicPage handler will throw a 404 if no page is found.
    # (For more information see TopicPage handler above)
    ('/(.*)', TopicPage),


    ], debug=True)

application = profiler.ProfilerWSGIMiddleware(application)
application = GAEBingoWSGIMiddleware(application)
application = request_cache.RequestCacheMiddleware(application)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
