#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import urllib
import urlparse
import logging
import re

from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache

from api.auth.decorators import developer_required

import webapp2

import devpanel
import bulk_update.handler
import request_cache
from gae_mini_profiler import profiler
from gae_bingo.middleware import GAEBingoWSGIMiddleware
import autocomplete
import coaches
import knowledgemap
import consts
import youtube_sync
import warmup
import library
import homepage

import search

import request_handler
from app import App
import util
import user_util
import exercise_statistics
import activity_summary
import exercises
import dashboard
import exercisestats.report
import exercisestats.report_json
import github
import paypal
import smarthistory
import topics
import goals.handlers
import stories
import summer
import common_core
import unisubs
import api.jsonify

import models
from models import UserData, Video, Url, ExerciseVideo, UserVideo, VideoLog, VideoSubtitles, Topic
from discussion import comments, notification, qa, voting, moderation
from about import blog, util_about
from phantom_users import util_notify
from badges import util_badges, custom_badges
from mailing_lists import util_mailing_lists
from profiles import util_profile
from custom_exceptions import MissingVideoException
from oauth_provider import apps as oauth_apps
from phantom_users.phantom_util import get_phantom_user_id_from_cookies
from phantom_users.cloner import Clone
from counters import user_counter
from notifications import UserNotifier
from nicknames import get_default_nickname_for
from image_cache import ImageCache
from api.auth.xsrf import ensure_xsrf_cookie
import redirects
import robots
from importer.handlers import ImportHandler
from gae_bingo.gae_bingo import bingo

class VideoDataTest(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        self.response.out.write('<html>')
        videos = Video.all()
        for video in videos:
            self.response.out.write('<P>Title: ' + video.title)

def get_mangled_topic_name(topic_name):
    for char in " :()":
        topic_name = topic_name.replace(char, "")
    return topic_name

class ViewVideo(request_handler.RequestHandler):

    @staticmethod
    def show_video(handler, readable_id, topic_id, redirect_to_canonical_url=False):
        topic = None

        if not readable_id:
            # Need to show some video here temporarily, using introductory algebra video
            template_values = {
                "video": { "youtube_id": "kpCJyQ2usJ4" },
                "top_level_topic": topic_id,
                "selected_nav_link": 'watch'
            }

#            bingo(['struggling_videos_landing'])
            handler.render_jinja2_template('viewvideo.html', template_values)
            return

        if topic_id is not None and len(topic_id) > 0:
            topic = Topic.get_by_id(topic_id)
            key_id = 0 if not topic else topic.key().id()

        # If a topic_id wasn't specified or the specified topic wasn't found
        # use the first topic for the requested video.
        if topic is None:
            # Get video by readable_id just to get the first topic for the video
            video = Video.get_for_readable_id(readable_id)
            if video is None:
                raise MissingVideoException("Missing video '%s'" % readable_id)

            topic = video.first_topic()
            if not topic:
                raise MissingVideoException("No topic has video '%s'" % readable_id)

            redirect_to_canonical_url = True

        if redirect_to_canonical_url:
            url = "/%s/v/%s" % (topic.get_extended_slug(), urllib.quote(readable_id))
            handler.redirect(url, True)
            return

        topic_data = topic.get_play_data()

        discussion_options = qa.add_template_values({}, handler.request)
        video_data = Video.get_play_data(readable_id, topic, discussion_options)
        if video_data is None:
            raise MissingVideoException("Missing video '%s'" % readable_id)

        template_values = {
            "topic_data": topic_data,
            "topic_data_json": api.jsonify.jsonify(topic_data),
            "video": video_data,
            "video_data_json": api.jsonify.jsonify(video_data),
            "selected_nav_link": 'watch'
        }

        bingo([
            'struggling_videos_landing',
            'suggested_activity_videos_landing',
            'suggested_activity_videos_landing_binary',
        ])
        handler.render_jinja2_template('viewvideo.html', template_values)

    # The handler itself is deprecated. The ShowContent handler is the canonical
    # handler now.
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

    def get(self):
        issue_type = self.request.get('type')
        self.write_response(issue_type, {'issue_labels': self.request.get('issue_labels'),})

    def write_response(self, issue_type, extra_template_values):
        user_agent = self.request.headers.get('User-Agent')
        if user_agent is None:
            user_agent = ''
        user_agent = user_agent.replace(',',';') # Commas delimit labels, so we don't want them
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
    def get(self):
        if self.request_bool("capability_disabled", default=False):
            raise CapabilityDisabledError("Simulate scheduled GAE downtime")
        else:
            # Even Watson isn't perfect
            raise Exception("What is Toronto?")

class ReadOnlyDowntime(request_handler.RequestHandler):
    def get(self):
        raise CapabilityDisabledError("App Engine maintenance period")

    def post(self):
        return self.get()

class SendToLog(request_handler.RequestHandler):
    def post(self):
        message = self.request_string("message", default="")
        if message:
            logging.critical("Manually sent to log: %s" % message)

class MobileFullSite(request_handler.RequestHandler):
    def get(self):
        self.set_mobile_full_site_cookie(True)
        self.redirect("/")

class MobileSite(request_handler.RequestHandler):
    def get(self):
        self.set_mobile_full_site_cookie(False)
        self.redirect("/")

class ViewFAQ(request_handler.RequestHandler):
    def get(self):
        self.redirect("/about/faq", True)
        return

class ViewGetInvolved(request_handler.RequestHandler):
    def get(self):
        self.redirect("/contribute", True)

class ViewContribute(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('contribute.html', {"selected_nav_link": "contribute"})

class ViewCredits(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('viewcredits.html', {"selected_nav_link": "contribute"})

class Donate(request_handler.RequestHandler):
    def get(self):
        self.redirect("/contribute", True)

class ViewTOS(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('tos.html', {"selected_nav_link": "tos"})

class ViewAPITOS(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('api-tos.html', {"selected_nav_link": "api-tos"})

class ViewPrivacyPolicy(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('privacy-policy.html', {"selected_nav_link": "privacy-policy"})

class ViewDMCA(request_handler.RequestHandler):
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

    def get(self):
        (old_email, new_email, prop) = self.get_email_params()
        if new_email == old_email:
            return bulk_update.handler.UpdateKind.get(self)
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
        gt_user = users.User(old_email[:-1] + chr(ord(old_email[-1])-1) + chr(127))
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

class Login(request_handler.RequestHandler):
    def get(self):
        return self.post()

    def post(self):
        cont = self.request_string('continue', default = "/")
        direct = self.request_bool('direct', default = False)

        openid_identifier = self.request.get('openid_identifier')
        if openid_identifier is not None and len(openid_identifier) > 0:
            if App.accepts_openid:
                self.redirect(users.create_login_url(cont, federated_identity = openid_identifier))
                return
            self.redirect(users.create_login_url(cont))
            return

        if App.facebook_app_secret is None:
            self.redirect(users.create_login_url(cont))
            return
        template_values = {
                           'continue': cont,
                           'direct': direct
                           }
        self.render_jinja2_template('login.html', template_values)

class MobileOAuthLogin(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('login_mobile_oauth.html', {
            "oauth_map_id": self.request_string("oauth_map_id", default=""),
            "anointed": self.request_bool("an", default=False),
            "view": self.request_string("view", default="")
        })

class PostLogin(request_handler.RequestHandler):
    def get(self):
        cont = self.request_string('continue', default = "/")

        # Immediately after login we make sure this user has a UserData entity
        user_data = UserData.current()
        if user_data:

            # Update email address if it has changed
            current_google_user = users.get_current_user()
            if current_google_user and current_google_user.email() != user_data.email:
                user_data.user_email = current_google_user.email()
                user_data.put()

            # If the user has a public profile, we stop "syncing" their username
            # from Facebook, as they now have an opportunity to set it themself
            if not user_data.username:
                user_data.update_nickname()

            # Set developer and moderator to True if user is admin
            if (not user_data.developer or not user_data.moderator) and users.is_current_user_admin():
                user_data.developer = True
                user_data.moderator = True
                user_data.put()

            # If user is brand new and has 0 points, migrate data
            phantom_id = get_phantom_user_id_from_cookies()
            if phantom_id:
                phantom_data = UserData.get_from_db_key_email(phantom_id)

                # First make sure user has 0 points and phantom user has some activity
                if user_data.points == 0 and phantom_data and phantom_data.points > 0:

                    # Make sure user has no students
                    if not user_data.has_students():

                        # Clear all "login" notifications
                        UserNotifier.clear_all(phantom_data)

                        # Update phantom user_data to real user_data
                        phantom_data.user_id = user_data.user_id
                        phantom_data.current_user = user_data.current_user
                        phantom_data.user_email = user_data.user_email
                        phantom_data.user_nickname = user_data.user_nickname

                        if phantom_data.put():
                            # Phantom user was just transitioned to real user
                            user_counter.add(1)
                            user_data.delete()

                        cont = "/newaccount?continue=%s" % cont
        else:

            # If nobody is logged in, clear any expired Facebook cookie that may be hanging around.
            if App.facebook_app_id:
                self.delete_cookie("fbsr_" + App.facebook_app_id)
                self.delete_cookie("fbs_" + App.facebook_app_id)

            logging.critical("Missing UserData during PostLogin, with id: %s, cookies: (%s), google user: %s" % (
                    util.get_current_user_id(), os.environ.get('HTTP_COOKIE', ''), users.get_current_user()
                )
            )

        # Always delete phantom user cookies on login
        self.delete_cookie('ureg_id')

        self.redirect(cont)

class Logout(request_handler.RequestHandler):
    def get(self):
        self.delete_cookie('ureg_id')

        # Delete Facebook cookie, which sets itself both on "www.ka.org" and ".www.ka.org"
        if App.facebook_app_id:
            self.delete_cookie_including_dot_domain('fbsr_' + App.facebook_app_id)
            self.delete_cookie_including_dot_domain('fbm_' + App.facebook_app_id)

        self.redirect(users.create_logout_url(self.request_string("continue", default="/")))

class Search(request_handler.RequestHandler):

    def get(self):
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
        # all_key_list.extend([result["key"] for result in topic_partial_results])
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

        topic_count = len(topics)

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
        if topics:
            if len(filtered_videos) > 0:
                for topic in topics:
                    topic.match_count = [(str(topic.key()) in video.topic_string_keys) for video in filtered_videos].count(True)
                topics = sorted(topics, key=lambda topic: -topic.match_count)
            else:
                for topic in topics:
                    topic.match_count = 0

        template_values.update({
                           'topics': topics,
                           'videos': filtered_videos,
                           'video_exercises': video_exercises,
                           'search_string': query,
                           'video_count': video_count,
                           'topic_count': topic_count,
                           })
        
        self.render_jinja2_template("searchresults.html", template_values)

class RedirectToJobvite(request_handler.RequestHandler):
    def get(self):
        self.redirect("http://hire.jobvite.com/CompanyJobs/Careers.aspx?k=JobListing&c=qd69Vfw7")

class RedirectToToolkit(request_handler.RequestHandler):
    def get(self):
        self.redirect("https://sites.google.com/a/khanacademy.org/schools/")

class PermanentRedirectToHome(request_handler.RequestHandler):
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

# This handler is used for the video player currently. In the future it will show
# topic pages and exercises as well.
# The URI format is a topic path followed by a type and resource identifier, i.e.:
#   /math/algebra/introduction-to-algebra/v/origins-of-algebra  (A video in topic "introduction-to-algebra" with ID "origins-of-algebra"
class ShowContent(request_handler.RequestHandler):
    @ensure_xsrf_cookie
    def get(self, path=None):

        if path:
            path_list = path.split('/')
            if len(path_list) >= 3:
                topic_id = path_list[-3]
                content_type = path_list[-2]
                content_id = path_list[-1]

                if content_type == "v":
                    ViewVideo.show_video(self, content_id, topic_id)
                    return

            if len(path_list) > 0:
                ViewVideo.show_video(self, None, path_list[0])

class ServeUserVideoCss(request_handler.RequestHandler):
    def get(self):
        user_data = UserData.current()
        if user_data == None:
            return

        user_video_css = models.UserVideoCss.get_for_user_data(user_data)
        self.response.headers['Content-Type'] = 'text/css'

        if user_video_css.version == user_data.uservideocss_version:
            # Don't cache if there's a version mismatch and update isn't finished
            self.response.headers['Cache-Control'] = 'public,max-age=1000000'

        self.response.out.write(user_video_css.video_css)

class RealtimeEntityCount(request_handler.RequestHandler):
    def get(self):
        if not App.is_dev_server:
            raise Exception("Only works on dev servers.")
        default_kinds = 'Exercise'
        kinds = self.request_string("kinds", default_kinds).split(',')
        for kind in kinds:
            count = getattr(models, kind).all().count(10000)
            self.response.out.write("%s: %d<br>" % (kind, count))

class MemcacheViewer(request_handler.RequestHandler):
    @developer_required
    def get(self):
        key = self.request_string("key", "__layer_cache_models._get_settings_dict__")
        namespace = self.request_string("namespace", App.version)
        values =  memcache.get(key, namespace=namespace)
        self.response.out.write("Memcache key %s = %s.<br>\n" % (key, values))
        if type(values) is dict:
            for k, value in values.iteritems():
                self.response.out.write("<p><b>%s</b>%s</p>" % (k, dict((key, getattr(value, key)) for key in dir(value))))
        if self.request_bool("clear", False):
            memcache.delete(key, namespace=namespace)

applicationSmartHistory = webapp2.WSGIApplication([
    ('/.*', smarthistory.SmartHistoryProxy)
])

application = webapp2.WSGIApplication([
    ('/', homepage.ViewHomePage),
    ('/about', util_about.ViewAbout),
    ('/about/blog', blog.ViewBlog),
    ('/about/blog/.*', blog.ViewBlogPost),
    ('/about/the-team', util_about.ViewAboutTheTeam),
    ('/about/getting-started', util_about.ViewGettingStarted),
    ('/about/discovery-lab', util_about.ViewDiscoveryLab ),
    ('/about/tos', ViewTOS ),
    ('/about/api-tos', ViewAPITOS),
    ('/about/privacy-policy', ViewPrivacyPolicy ),
    ('/about/dmca', ViewDMCA ),
    ('/contribute', ViewContribute ),
    ('/contribute/credits', ViewCredits ),
    ('/frequently-asked-questions', util_about.ViewFAQ),
    ('/about/faq', util_about.ViewFAQ),
    ('/downloads', util_about.ViewDownloads),
    ('/about/downloads', util_about.ViewDownloads),
    ('/getinvolved', ViewGetInvolved),
    ('/donate', Donate),
    ('/exercisedashboard', exercises.ViewAllExercises),

    ('/stories/submit', stories.SubmitStory),
    ('/stories/?.*', stories.ViewStories),

    # Issues a command to re-generate the library content.
    ('/library_content', library.GenerateLibraryContent),

    ('/exercise/(.+)', exercises.ViewExercise), # /exercises/addition_1
    ('/exercises', exercises.ViewExercise), # This old /exercises?exid=addition_1 URL pattern is deprecated
    ('/review', exercises.ViewExercise),

    ('/khan-exercises/exercises/.*', exercises.RawExercise),
    ('/viewexercisesonmap', exercises.ViewAllExercises),
    ('/editexercise', exercises.EditExercise),
    ('/updateexercise', exercises.UpdateExercise),
    ('/moveexercisemapnodes', exercises.MoveMapNodes),
    ('/admin94040', exercises.ExerciseAdmin),
    ('/video/(.*)', ViewVideo),
    ('/v/(.*)', ViewVideo),
    ('/video', ViewVideo), # Backwards URL compatibility
    ('/reportissue', ReportIssue),
    ('/search', Search),
    ('/savemapcoords', knowledgemap.SaveMapCoords),
    ('/saveexpandedallexercises', knowledgemap.SaveExpandedAllExercises),
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
    ('/admin/realtimeentitycount', RealtimeEntityCount),
    ('/admin/unisubs', unisubs.ReportHandler),
    ('/admin/unisubs/import', unisubs.ImportHandler),

    ('/devadmin', devpanel.Panel),
    ('/devadmin/emailchange', devpanel.MergeUsers),
    ('/devadmin/managedevs', devpanel.Manage),
    ('/devadmin/managecoworkers', devpanel.ManageCoworkers),
    ('/devadmin/managecommoncore', devpanel.ManageCommonCore),
    ('/commoncore', common_core.CommonCore),
    ('/staging/commoncore', common_core.CommonCore),
    ('/devadmin/content', topics.EditContent),
    ('/devadmin/memcacheviewer', MemcacheViewer),

    ('/coaches', coaches.ViewCoaches),
    ('/students', coaches.ViewStudents),
    ('/registercoach', coaches.RegisterCoach),
    ('/unregistercoach', coaches.UnregisterCoach),
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

    ('/login', Login),
    ('/login/mobileoauth', MobileOAuthLogin),
    ('/postlogin', PostLogin),
    ('/logout', Logout),

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
    ('/discussion/videofeedbacknotificationlist', notification.VideoFeedbackNotificationList),
    ('/discussion/videofeedbacknotificationfeed', notification.VideoFeedbackNotificationFeed),

    ('/discussion/mod', moderation.ModPanel),
    ('/discussion/moderatorlist', moderation.RedirectToModPanel),
    ('/discussion/flaggedfeedback', moderation.RedirectToModPanel),
    ('/discussion/mod/flaggedfeedback', moderation.FlaggedFeedback),
    ('/discussion/mod/moderatorlist', moderation.ModeratorList),
    ('/discussion/mod/bannedlist', moderation.BannedList),

    ('/githubpost', github.NewPost),
    ('/githubcomment', github.NewComment),

    ('/toolkit', RedirectToToolkit),

    ('/paypal/autoreturn', paypal.AutoReturn),
    ('/paypal/ipn', paypal.IPN),

    ('/badges/view', util_badges.ViewBadges),
    ('/badges/custom/create', custom_badges.CreateCustomBadge),
    ('/badges/custom/award', custom_badges.AwardCustomBadge),

    ('/notifierclose', util_notify.ToggleNotify),
    ('/newaccount', Clone),

    ('/jobs', RedirectToJobvite),
    ('/jobs/.*', RedirectToJobvite),

    ('/dashboard', dashboard.Dashboard),
    ('/contentdash', dashboard.ContentDashboard),
    ('/admin/dashboard/record_statistics', dashboard.RecordStatistics),
    ('/admin/entitycounts', dashboard.EntityCounts),

    ('/sendtolog', SendToLog),

    ('/user_video_css', ServeUserVideoCss),

    ('/admin/exercisestats/collectfancyexercisestatistics', exercisestats.CollectFancyExerciseStatistics),
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

    ('/robots.txt', robots.RobotsTxt),

    ('/r/.*', redirects.Redirect),
    ('/redirects', redirects.List),
    ('/redirects/add', redirects.Add),
    ('/redirects/remove', redirects.Remove),

    ('/importer', ImportHandler),

    # Redirect any links to old JSP version
    ('/.*\.jsp', PermanentRedirectToHome),
    ('/index\.html', PermanentRedirectToHome),

    ('/_ah/warmup.*', warmup.Warmup),

    # Content glob comes in dead last so it doesn't conflict with any other routes (See ShowContent)
    ('/(.*)', ShowContent),

    ], debug=True)

application = profiler.ProfilerWSGIMiddleware(application)
application = GAEBingoWSGIMiddleware(application)
application = request_cache.RequestCacheMiddleware(application)

def main():
    if os.environ["SERVER_NAME"] == "smarthistory.khanacademy.org":
        run_wsgi_app(applicationSmartHistory)
    else:
        run_wsgi_app(application)

if __name__ == '__main__':
    main()
