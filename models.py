#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime, logging

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import math
import urllib
import cPickle as pickle
import random
import itertools

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api.datastore_errors import Rollback
from google.appengine.ext import deferred
from google.appengine.api import taskqueue
from google.appengine.ext.db import TransactionFailedError
from api.jsonify import jsonify

from google.appengine.ext import db
import object_property
import util
import user_util
import consts
import points
from search import Searchable
from app import App
import layer_cache
import request_cache
from discussion import models_discussion
from experiments import InteractiveTranscriptExperiment
from topics_list import all_topics_list
import nicknames
from counters import user_counter
from facebook_util import is_facebook_user_id, FACEBOOK_ID_PREFIX
from accuracy_model import AccuracyModel, InvFnExponentialNormalizer
from decorators import clamp, synchronized_with_memcache
import base64, os

from image_cache import ImageCache

from auth import age_util
from auth.models import CredentialedUser
from templatefilters import slugify
from gae_bingo.gae_bingo import bingo
from gae_bingo.models import GAEBingoIdentityModel
from experiments import StrugglingExperiment
import re


class BackupModel(db.Model):
    """Back up this model

    This is used for automatic daily backups of all models. If you would like
    your model to be backed up (off of App Engine), just inherit from
    BackupModel.
    """
    backup_timestamp = db.DateTimeProperty(auto_now=True)

# Setting stores per-application key-value pairs
# for app-wide settings that must be synchronized
# across all GAE instances.

class Setting(db.Model):

    value = db.StringProperty(indexed=False)

    @staticmethod
    def entity_group_key():
        return db.Key.from_path('Settings', 'default_settings')

    @staticmethod
    def _get_or_set_with_key(key, val=None):
        if val is None:
            return Setting._cache_get_by_key_name(key)
        else:
            setting = Setting(Setting.entity_group_key(), key, value=str(val))
            db.put(setting)
            Setting._get_settings_dict(bust_cache=True)
            return setting.value

    @staticmethod
    def _cache_get_by_key_name(key):
        setting = Setting._get_settings_dict().get(key)
        if setting is not None:
            return setting.value
        return None

    @staticmethod
    @request_cache.cache()
    @layer_cache.cache(layer=layer_cache.Layers.Memcache)
    def _get_settings_dict():
        # ancestor query to ensure consistent results
        query = Setting.all().ancestor(Setting.entity_group_key())
        results = dict((setting.key().name(), setting) for setting in query.fetch(20))
        return results

    @staticmethod
    def cached_content_add_date(val=None):
        return Setting._get_or_set_with_key("cached_content_add_date", val)

    @staticmethod
    def topic_tree_version(val=None):
        return Setting._get_or_set_with_key("topic_tree_version", val)

    @staticmethod
    def cached_exercises_date(val=None):
        return Setting._get_or_set_with_key("cached_exercises_date", val)

    @staticmethod
    def count_videos(val=None):
        return Setting._get_or_set_with_key("count_videos", val) or 0

    @staticmethod
    def last_youtube_sync_generation_start(val=None):
        return Setting._get_or_set_with_key("last_youtube_sync_generation_start", val) or 0

    @staticmethod
    def topic_admin_task_message(val=None):
        return Setting._get_or_set_with_key("topic_admin_task_message", val)

    @staticmethod
    def smarthistory_version(val=None):
        return Setting._get_or_set_with_key("smarthistory_version", val) or 0

    @staticmethod
    def classtime_report_method(val=None):
        return Setting._get_or_set_with_key("classtime_report_method", val)

    @staticmethod
    def classtime_report_startdate(val=None):
        return Setting._get_or_set_with_key("classtime_report_startdate", val)

class Exercise(db.Model):

    name = db.StringProperty()
    short_display_name = db.StringProperty(default="")
    prerequisites = db.StringListProperty()
    covers = db.StringListProperty()
    v_position = db.IntegerProperty() # actually horizontal position on knowledge map
    h_position = db.IntegerProperty() # actually vertical position on knowledge map
    seconds_per_fast_problem = db.FloatProperty(default=consts.INITIAL_SECONDS_PER_FAST_PROBLEM) # Seconds expected to finish a problem 'quickly' for badge calculation

    # True if this exercise is live and visible to all users.
    # Non-live exercises are only visible to admins.
    live = db.BooleanProperty(default=False)

    summative = db.BooleanProperty(default=False)

    # Teachers contribute raw html with embedded CSS and JS
    # and we sanitize it with Caja before displaying it to
    # students.
    author = db.UserProperty()
    raw_html = db.TextProperty()
    last_modified = db.DateTimeProperty()
    creation_date = db.DateTimeProperty(auto_now_add=True, default=datetime.datetime(2011, 1, 1))
    description = db.TextProperty()
    tags = db.StringListProperty()

    # List of parent topics
    topic_string_keys = object_property.TsvProperty(indexed=False)

    _serialize_blacklist = [
            "author", "raw_html", "last_modified",
            "coverers", "prerequisites_ex", "assigned",
            "topic_string_keys", "related_video_keys"
            ]

    @staticmethod
    def get_relative_url(exercise_name):
        return "/exercise/%s" % exercise_name

    @property
    def relative_url(self):
        return Exercise.get_relative_url(self.name)

    @property
    def ka_url(self):
        return util.absolute_url(self.relative_url)

    @staticmethod
    def get_by_name(name, version=None):
        dict_exercises = Exercise._get_dict_use_cache_unsafe()
        if dict_exercises.has_key(name):
            if dict_exercises[name].is_visible_to_current_user():
                exercise = dict_exercises[name]
                # if there is a version check to see if there are any updates to the video
                if version:
                    change = VersionContentChange.get_change_for_content(exercise, version)
                    if change:
                        exercise = change.updated_content(exercise)
                return exercise
        return None

    @staticmethod
    def to_display_name(name):
        if name:
            return name.replace('_', ' ').capitalize()
        return ""

    @property
    def display_name(self):
        return Exercise.to_display_name(self.name)

    @property
    def sha1(self):
        return exercise_sha1(self)

    @staticmethod
    def to_short_name(name):
        exercise = Exercise.get_by_name(name)
        return exercise.short_name() if exercise else ""

    def short_name(self):
        return (self.short_display_name or self.display_name)[:11]

    def is_visible_to_current_user(self):
        return self.live or user_util.is_current_user_developer()

    def has_topic(self):
        return bool(self.topic_string_keys)

    def first_topic(self):
        """ Returns this Exercise's first non-hidden parent Topic """

        if self.topic_string_keys:
            return db.get(self.topic_string_keys[0])

        return None

    def related_videos_query(self):
        query = ExerciseVideo.all()
        query.filter('exercise =', self.key()).order('exercise_order')
        return query

    @layer_cache.cache_with_key_fxn(lambda self: "related_videos_%s_%s" %
        (self.key(), Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def related_videos_fetch(self):
        exercise_videos = self.related_videos_query().fetch(10)
        for exercise_video in exercise_videos:
            exercise_video.video # Pre-cache video entity
        return exercise_videos

    @staticmethod
    def add_related_videos_prop(exercise_dict, evs=None, video_dict=None):
        if video_dict is None:
            video_dict = {}

        # if no pregotten evs were passed in asynchrnously get them for all
        # exercises in exercise_dict
        if evs is None:
            queries = []
            for exercise in exercise_dict.values():
                queries.append(exercise.related_videos_query())

            tasks = util.async_queries(queries, limit=10000)
            evs = [ev for task in tasks for ev in task.get_result()]

        # if too many evs were passed in filter out exercise_videos which are
        # not looking at one of the exercises in exercise_dict
        evs = [ev for ev in evs
               if ExerciseVideo.exercise.get_value_for_datastore(ev)
               in exercise_dict.keys()]

        # add any videos to video_dict that we need and are not already in
        # the video_dict passed in
        extra_video_keys = [ExerciseVideo.video.get_value_for_datastore(ev)
            for ev in evs if ExerciseVideo.video.get_value_for_datastore(ev)
            not in video_dict.keys()]
        extra_videos = db.get(extra_video_keys)
        extra_video_dict = dict((v.key(), v) for v in extra_videos)
        video_dict.update(extra_video_dict)

        # buid a ev_dict in the form
        # ev_dict[exercise_key][video_key] = (video_readable_id, ev.exercise_order)
        ev_dict = {}
        for ev in evs:
            exercise_key = ExerciseVideo.exercise.get_value_for_datastore(ev)
            video_key = ExerciseVideo.video.get_value_for_datastore(ev)
            video_readable_id = video_dict[video_key].readable_id

            if exercise_key not in ev_dict:
                ev_dict[exercise_key] = {}

            ev_dict[exercise_key][video_key] = (video_readable_id, ev.exercise_order)

        # update all exercises to include the related_videos in their right
        # orders
        for exercise in exercise_dict.values():
            related_videos = (ev_dict[exercise.key()]
                              if exercise.key() in ev_dict else {})
            related_videos = sorted(related_videos.items(),
                                    key=lambda i:i[1][1])
            exercise.related_video_keys = map(lambda i: i[0], related_videos)
            exercise.related_videos = map(lambda i: i[1][0], related_videos)

    # followup_exercises reverse walks the prerequisites to give you
    # the exercises that list the current exercise as its prerequisite.
    # i.e. follow this exercise up with these other exercises
    def followup_exercises(self):
        return [exercise for exercise in Exercise.get_all_use_cache() if self.name in exercise.prerequisites]

    @classmethod
    def all(cls, live_only=False, **kwargs):
        query = super(Exercise, cls).all(**kwargs)
        if live_only or not user_util.is_current_user_developer():
            query.filter("live =", True)
        return query

    @classmethod
    def all_unsafe(cls):
        return super(Exercise, cls).all()

    @staticmethod
    def get_all_use_cache():
        if user_util.is_current_user_developer():
            return Exercise._get_all_use_cache_unsafe()
        else:
            return Exercise._get_all_use_cache_safe()

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda * args, **kwargs: "all_exercises_unsafe_%s" % 
            Setting.cached_exercises_date())
    def _get_all_use_cache_unsafe():
        query = Exercise.all_unsafe().order('h_position')
        return query.fetch(1000) # TODO(Ben) this limit is tenuous

    @staticmethod
    def _get_all_use_cache_safe():
        return filter(lambda exercise: exercise.live, Exercise._get_all_use_cache_unsafe())

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda * args, **kwargs: "all_exercises_dict_unsafe_%s" % 
            Setting.cached_exercises_date())
    def _get_dict_use_cache_unsafe():
        exercises = Exercise._get_all_use_cache_unsafe()
        dict_exercises = {}
        for exercise in exercises:
            dict_exercises[exercise.name] = exercise
        return dict_exercises

    @staticmethod
    @layer_cache.cache(expiration=3600)
    def get_count():
        return Exercise.all(live_only=True).count()

    def put(self):
        Setting.cached_exercises_date(str(datetime.datetime.now()))
        db.Model.put(self)
        Exercise.get_count(bust_cache=True)

    @staticmethod
    def get_dict(query, fxn_key):
        exercise_dict = {}
        for exercise in query.fetch(10000):
            exercise_dict[fxn_key(exercise)] = exercise
        return exercise_dict


class UserExercise(db.Model):

    user = db.UserProperty()
    exercise = db.StringProperty()
    exercise_model = db.ReferenceProperty(Exercise)
    streak = db.IntegerProperty(default=0)
    _progress = db.FloatProperty(default=None, indexed=False)  # A continuous value >= 0.0, where 1.0 means proficiency. This measure abstracts away the internal proficiency model.
    longest_streak = db.IntegerProperty(default=0, indexed=False)
    first_done = db.DateTimeProperty(auto_now_add=True)
    last_done = db.DateTimeProperty()
    total_done = db.IntegerProperty(default=0)
    total_correct = db.IntegerProperty(default=0)
    last_review = db.DateTimeProperty(default=datetime.datetime.min)
    review_interval_secs = db.IntegerProperty(default=(60 * 60 * 24 * consts.DEFAULT_REVIEW_INTERVAL_DAYS), indexed=False) # Default 7 days until review
    proficient_date = db.DateTimeProperty()
    seconds_per_fast_problem = db.FloatProperty(default=consts.INITIAL_SECONDS_PER_FAST_PROBLEM, indexed=False) # Seconds expected to finish a problem 'quickly' for badge calculation
    _accuracy_model = object_property.ObjectProperty()  # Stateful function object that estimates P(next problem correct). May not exist for old UserExercise objects (but will be created when needed).

    _USER_EXERCISE_KEY_FORMAT = "UserExercise.all().filter('user = '%s')"

    _serialize_blacklist = ["review_interval_secs", "_progress", "_accuracy_model"]

    _MIN_PROBLEMS_FROM_ACCURACY_MODEL = AccuracyModel.min_streak_till_threshold(consts.PROFICIENCY_ACCURACY_THRESHOLD)
    _MIN_PROBLEMS_REQUIRED = max(_MIN_PROBLEMS_FROM_ACCURACY_MODEL, consts.MIN_PROBLEMS_IMPOSED)

    # Bound function objects to normalize the progress bar display from a probability
    # TODO(david): This is a bit of a hack to not have the normalizer move too
    #     slowly if the user got a lot of wrongs.
    _all_correct_normalizer = InvFnExponentialNormalizer(
        accuracy_model=AccuracyModel().update(correct=False),
        proficiency_threshold=AccuracyModel.simulate([True] * _MIN_PROBLEMS_REQUIRED)
    ).normalize
    _had_wrong_normalizer = InvFnExponentialNormalizer(
        accuracy_model=AccuracyModel().update([False] * 3),
        proficiency_threshold=consts.PROFICIENCY_ACCURACY_THRESHOLD
    ).normalize

    @property
    def exercise_states(self):
        user_exercise_graph = self.get_user_exercise_graph()
        if user_exercise_graph:
            return user_exercise_graph.states(self.exercise)
        return None

    def accuracy_model(self):
        if self._accuracy_model is None:
            self._accuracy_model = AccuracyModel(self)
        return self._accuracy_model

    # Faciliate transition for old objects that did not have the _progress property
    @property
    @clamp(0.0, 1.0)
    def progress(self):
        if self._progress is None:
            self._progress = self._get_progress_from_current_state()
        return self._progress

    def update_proficiency_model(self, correct):
        if not correct:
            self.streak = 0

        self.accuracy_model().update(correct)
        self._progress = self._get_progress_from_current_state()

    @clamp(0.0, 1.0)
    def _get_progress_from_current_state(self):

        if self.total_correct == 0:
            return 0.0

        prediction = self.accuracy_model().predict()

        if self.accuracy_model().total_done <= self.accuracy_model().total_correct():
            # Impose a minimum number of problems required to be done.
            normalized_prediction = UserExercise._all_correct_normalizer(prediction)
        else:
            normalized_prediction = UserExercise._had_wrong_normalizer(prediction)

        return normalized_prediction

    @staticmethod
    def to_progress_display(num):
        return '%.0f%%' % math.floor(num * 100.0) if num <= consts.MAX_PROGRESS_SHOWN else 'Max'

    def progress_display(self):
        return UserExercise.to_progress_display(self.progress)

    @staticmethod
    def get_key_for_email(email):
        return UserExercise._USER_EXERCISE_KEY_FORMAT % email

    @staticmethod
    def get_for_user_data(user_data):
        query = UserExercise.all()
        query.filter('user =', user_data.user)
        return query

    def get_user_data(self):
        user_data = None

        if hasattr(self, "_user_data"):
            user_data = self._user_data
        else:
            user_data = UserData.get_from_db_key_email(self.user.email())

        if not user_data:
            logging.critical("Empty user data for UserExercise w/ .user = %s" % self.user)

        return user_data

    def get_user_exercise_graph(self):
        user_exercise_graph = None

        if hasattr(self, "_user_exercise_graph"):
            user_exercise_graph = self._user_exercise_graph
        else:
            user_exercise_graph = UserExerciseGraph.get(self.get_user_data())

        return user_exercise_graph

    def belongs_to(self, user_data):
        return user_data and self.user.email().lower() == user_data.key_email.lower()

    def is_struggling(self, struggling_model=None):
        """ Whether or not the user is currently "struggling" in this exercise
        for a given struggling model. Note that regardless of struggling model,
        if the last question was correct, the student is not considered
        struggling.
        """
        if self.has_been_proficient():
            return False

        return self.history_indicates_struggling(struggling_model)

    # TODO(benkomalo): collapse this method with is_struggling above.
    def history_indicates_struggling(self, struggling_model=None):
        """ Whether or not the history of answers indicates that the user
        is struggling on this exercise.

        Does not take into consideration if the last question was correct. """

        if struggling_model is None or struggling_model == 'old':
            return self._is_struggling_old()
        else:
            # accuracy based model.
            param = float(struggling_model.split('_')[1])
            return self.accuracy_model().is_struggling(
                    param=param,
                    minimum_accuracy=consts.PROFICIENCY_ACCURACY_THRESHOLD,
                    minimum_attempts=consts.MIN_PROBLEMS_IMPOSED)

    def _is_struggling_old(self):
        return self.streak == 0 and self.total_done > 20

    @staticmethod
    @clamp(datetime.timedelta(days=consts.MIN_REVIEW_INTERVAL_DAYS),
            datetime.timedelta(days=consts.MAX_REVIEW_INTERVAL_DAYS))
    def get_review_interval_from_seconds(seconds):
        return datetime.timedelta(seconds=seconds)

    def has_been_proficient(self):
        return self.proficient_date is not None

    def get_review_interval(self):
        return UserExercise.get_review_interval_from_seconds(self.review_interval_secs)

    def schedule_review(self, correct, now=None):
        if now is None:
            now = datetime.datetime.now()

        # If the user is not now and never has been proficient, don't schedule a review
        if self.progress < 1.0 and not self.has_been_proficient():
            return

        # If the user is hitting a new streak either for the first time or after having lost
        # proficiency, reset their review interval counter.
        if self.progress >= 1.0:
            self.review_interval_secs = 60 * 60 * 24 * consts.DEFAULT_REVIEW_INTERVAL_DAYS

        review_interval = self.get_review_interval()

        # If we correctly did this review while it was in a review state, and
        # the previous review was correct, extend the review interval
        if correct and self.last_review != datetime.datetime.min:
            time_since_last_review = now - self.last_review
            if time_since_last_review >= review_interval:
                review_interval = time_since_last_review * 2

        if correct:
            self.last_review = now
        else:
            self.last_review = datetime.datetime.min
            review_interval = review_interval // 2

        self.review_interval_secs = review_interval.days * 86400 + review_interval.seconds

    def set_proficient(self, user_data):
        if self.exercise in user_data.proficient_exercises:
            return

        self.proficient_date = datetime.datetime.now()

        user_data.proficient_exercises.append(self.exercise)
        user_data.need_to_reassess = True
        user_data.put()

        util_notify.update(user_data, self, False, True)

        if self.exercise in UserData.conversion_test_hard_exercises:
            bingo('hints_gained_proficiency_hard_binary')
        elif self.exercise in UserData.conversion_test_easy_exercises:
            bingo('hints_gained_proficiency_easy_binary')

    @classmethod
    def from_json(cls, json, user_data):
        '''This method exists for testing convenience only. It's called only
        by code that runs in exclusively in development mode. Do not rely on
        this method in production code. If you need to break this code to
        implement some new feature, feel free!
        '''
        exercise = Exercise.get_by_name(json['exercise'])
        if not exercise:
            return None

        # this is probably completely broken as we don't serialize anywhere near
        # all the properties that UserExercise has. Still, let's see if it works
        return cls(
            key_name=exercise.name,
            parent=user_data,
            user=user_data.user,
            exercise=exercise.name,
            exercise_model=exercise,
            streak=int(json['streak']),
            longest_streak=int(json['longest_streak']),
            first_done=util.parse_iso8601(json['first_done']),
            last_done=util.coalesce(util.parse_iso8601, json['last_done']),
            total_done=int(json['total_done']),
            _accuracy_model=AccuracyModel()
        )

    @classmethod
    def from_dict(cls, attrs, user_data):
        """ Create a UserExercise model from a dictionary of attributes
        and a UserData model. This is useful for creating these objects
        from the property dictionaries cached in UserExerciseCache.
        """

        user_exercise = cls(
            key_name=attrs["name"],
            parent=user_data,
            user=user_data.user,
            exercise=attrs["name"],
            _progress=attrs["progress"],
        )

        for key in attrs:
            if hasattr(user_exercise, key):
                try:
                    setattr(user_exercise, key, attrs[key])
                except AttributeError:
                    # Some attributes are unsettable -- ignore
                    pass

        return user_exercise

    @staticmethod
    def next_in_topic(user_data, topic, n=3, queued=[]):
        """ Returns the next n suggested user exercises for this topic,
        all prepped and ready for JSONification, as a tuple.

        TODO(save us, Jace): *This* is where the magic will happen.
        """

        exercises = topic.get_exercises(include_descendants=True)
        graph = UserExerciseGraph.get(user_data, exercises_allowed=exercises)

        # Start of by doing exercises that are in review
        stack_dicts = graph.review_graph_dicts()

        if len(stack_dicts) < n:
            # Now get all boundary exercises (those that aren't proficient and
            # aren't covered by other boundary exercises)
            frontier = UserExerciseGraph.get_boundary_names(graph.graph)
            frontier_dicts = [graph.graph_dict(exid) for exid in frontier]

            # If we don't have *any* boundary exercises, fill things out with the other
            # topic exercises. Note that if we have at least one boundary exercise, we don't
            # want to add others to the mix because they may screw w/ the boundary conditions
            # by adding a too-difficult exercise, etc.
            if len(frontier_dicts) == 0:
                frontier_dicts = graph.graph_dicts()

            # Now we sort the exercises by last_done and progress. If five exercises
            # all have the same progress, we want to send the user the one they did
            # least recently. Otherwise, we send the exercise that is most lacking in
            # progress.
            sorted_dicts = sorted(frontier_dicts, key=lambda d: d.get("last_done", None) or datetime.datetime.min)
            sorted_dicts = sorted(sorted_dicts, key=lambda d: d["progress"])

            stack_dicts += sorted_dicts

        # Build up UserExercise objects from our graph dicts
        user_exercises = [UserExercise.from_dict(d, user_data) for d in stack_dicts]

        return UserExercise._prepare_for_stack_api(user_exercises, n, queued)

    @staticmethod
    def next_in_review(user_data, n=3, queued=[]):
        """ Returns the next n suggested user exercises for this user's
        review mode, all prepped and ready for JSONification
        """
        graph = UserExerciseGraph.get(user_data)

        # Build up UserExercise objects from our graph dicts
        user_exercises = [UserExercise.from_dict(d, user_data) for d in graph.review_graph_dicts()]

        return UserExercise._prepare_for_stack_api(user_exercises, n, queued)

    @staticmethod
    def next_in_practice(user_data, exercise):
        """ Returns single user exercise used to practice specified exercise,
        all prepped and ready for JSONification
        """
        graph = UserExerciseGraph.get(user_data)
        user_exercise = UserExercise.from_dict(graph.graph_dict(exercise.name), user_data)
        return UserExercise._prepare_for_stack_api([user_exercise])

    @staticmethod
    def _prepare_for_stack_api(user_exercises, n=3, queued=[]):
        """ Returns the passed-in list of UserExercises, with additional properties
        added in preparation for JSONification by our API.

        Limits user_exercises returned to n, and filters out any user_exercises
        that are already queued up in the stack.

        TODO: when we eventually have support for various API projections, get rid
        of this manual property additions.
        """
        # Filter out already queued exercises
        user_exercises = [u_e for u_e in user_exercises if u_e.exercise not in queued][:n]

        for user_exercise in user_exercises:
            exercise = Exercise.get_by_name(user_exercise.exercise)

            # Attach related videos before sending down
            exercise.related_videos = [exercise_video.video for exercise_video in exercise.related_videos_fetch()]

            for video in exercise.related_videos:
                # TODO: this property is used by khan-exercises to render the progress
                # icon for related videos. If we decide to expose ids for all models via the API,
                # this will go away.
                video.id = video.key().id()

            user_exercise.exercise_model = exercise

        return user_exercises

class CoachRequest(db.Model):
    coach_requesting = db.UserProperty()
    student_requested = db.UserProperty()

    @property
    def coach_requesting_data(self):
        if not hasattr(self, "coach_user_data"):
            self.coach_user_data = UserData.get_from_db_key_email(self.coach_requesting.email())
        return self.coach_user_data

    @property
    def student_requested_data(self):
        if not hasattr(self, "student_user_data"):
            self.student_user_data = UserData.get_from_db_key_email(self.student_requested.email())
        return self.student_user_data

    @staticmethod
    def key_for(user_data_coach, user_data_student):
        return "%s_request_for_%s" % (user_data_coach.key_email, user_data_student.key_email)

    @staticmethod
    def get_for(user_data_coach, user_data_student):
        return CoachRequest.get_by_key_name(CoachRequest.key_for(user_data_coach, user_data_student))

    @staticmethod
    def get_or_insert_for(user_data_coach, user_data_student):
        return CoachRequest.get_or_insert(
                key_name=CoachRequest.key_for(user_data_coach, user_data_student),
                coach_requesting=user_data_coach.user,
                student_requested=user_data_student.user,
                )

    @staticmethod
    def get_for_student(user_data_student):
        return CoachRequest.all().filter("student_requested = ", user_data_student.user)

    @staticmethod
    def get_for_coach(user_data_coach):
        return CoachRequest.all().filter("coach_requesting = ", user_data_coach.user)

class StudentList(db.Model):
    name = db.StringProperty()
    coaches = db.ListProperty(db.Key)

    def delete(self, *args, **kwargs):
        self.remove_all_students()
        db.Model.delete(self, *args, **kwargs)

    def remove_all_students(self):
        students = self.get_students_data()
        for s in students:
            s.student_lists.remove(self.key())
        db.put(students)

    @property
    def students(self):
        return UserData.all().filter("student_lists = ", self.key())

    # these methods have the same interface as the methods on UserData
    def get_students_data(self):
        return [s for s in self.students]

    @staticmethod
    def get_for_coach(key):
        query = StudentList.all()
        query.filter("coaches = ", key)
        return query

class UserVideoCss(db.Model):
    user = db.UserProperty()
    video_css = db.TextProperty()
    pickled_dict = db.BlobProperty()
    last_modified = db.DateTimeProperty(required=True, auto_now=True, indexed=False)
    version = db.IntegerProperty(default=0, indexed=False)

    STARTED, COMPLETED = range(2)

    @staticmethod
    def get_for_user_data(user_data):
        p = pickle.dumps({'started': set([]), 'completed': set([])})
        return UserVideoCss.get_or_insert(UserVideoCss._key_for(user_data),
                                          user=user_data.user,
                                          video_css='',
                                          pickled_dict=p,
                                          )

    @staticmethod
    def _key_for(user_data):
        return 'user_video_css_%s' % user_data.key_email

    @staticmethod
    def set_started(user_data, video, version):
        """ Enqueues a task to asynchronously update the UserVideoCss to
        indicate the user has started the video. """
        deferred.defer(set_css_deferred, user_data.key(), video.key(),
                       UserVideoCss.STARTED, version,
                       _queue="video-log-queue",
                       _url="/_ah/queue/deferred_videolog")

    @staticmethod
    def set_completed(user_data, video, version):
        """ Enqueues a task to asynchronously update the UserVideoCss to
        indicate the user has completed the video. """
        deferred.defer(set_css_deferred, user_data.key(), video.key(),
                       UserVideoCss.COMPLETED, version,
                       _queue="video-log-queue",
                       _url="/_ah/queue/deferred_videolog")

    @staticmethod
    def _chunker(seq, size):
        return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))

    def load_pickled(self):
        max_selectors = 20
        css_list = []
        css = pickle.loads(self.pickled_dict)

        started_css = '{background-image:url(/images/video-indicator-started.png);padding-left:14px;}'
        complete_css = '{background-image:url(/images/video-indicator-complete.png);padding-left:14px;}'

        for id in UserVideoCss._chunker(list(css['started']), max_selectors):
            css_list.append(','.join(id))
            css_list.append(started_css)

        for id in UserVideoCss._chunker(list(css['completed']), max_selectors):
            css_list.append(','.join(id))
            css_list.append(complete_css)

        self.video_css = ''.join(css_list)

def set_css_deferred(user_data_key, video_key, status, version):
    user_data = UserData.get(user_data_key)
    uvc = UserVideoCss.get_for_user_data(user_data)
    css = pickle.loads(uvc.pickled_dict)

    id = '.v%d' % video_key.id()
    if status == UserVideoCss.STARTED:
        if id in css['completed']:
            logging.warn("video [%s] for [%s] went from completed->started. ignoring." %
                         (video_key, user_data_key))
        else:
            css['started'].add(id)
    else:
        css['started'].discard(id)
        css['completed'].add(id)

    uvc.pickled_dict = pickle.dumps(css)
    uvc.load_pickled()

    # if set_css_deferred runs out of order then we bump the version number
    # to break the cache
    if version < uvc.version:
        version = uvc.version + 1
        user_data.uservideocss_version += 1
        db.put(user_data)

    uvc.version = version
    db.put(uvc)

class UniqueUsername(db.Model):

    # The username value selected by the user.
    username = db.StringProperty()

    # A date indicating when the username was released.
    # This is useful to block off usernames, particularly after they were just
    # released, so they can be put in a holding period.
    # This will be set to an "infinitely" far-futures date while the username
    # is in use
    release_date = db.DateTimeProperty()

    # The user_id value of the UserData that claimed this username.
    # NOTE - may be None for some old UniqueUsername objects, or if it was
    # just blocked off for development.
    claimer_id = db.StringProperty()

    @staticmethod
    def build_key_name(username):
        """ Builds a unique, canonical version of a username. """
        if username is None:
            logging.error("Trying to build a key_name for a null username!")
            return ""
        return username.replace('.', '').lower()

    # Usernames must be at least 3 characters long (excluding periods), must
    # start with a letter
    VALID_KEY_NAME_RE = re.compile('^[a-z][a-z0-9]{2,}$')

    @staticmethod
    def is_username_too_short(username, key_name=None):
        if key_name is None:
            key_name = UniqueUsername.build_key_name(username)
        return len(key_name) < 3

    @staticmethod
    def is_valid_username(username, key_name=None):
        """ Determines if a candidate for a username is valid
        according to the limitations we enforce on usernames.

        Usernames must be at least 3 characters long (excluding dots), start
        with a letter and be alphanumeric (ascii only).
        """
        if username.startswith('.'):
            return False
        if key_name is None:
            key_name = UniqueUsername.build_key_name(username)
        return UniqueUsername.VALID_KEY_NAME_RE.match(key_name) is not None

    @staticmethod
    def is_available_username(username, key_name=None, clock=None):
        if key_name is None:
            key_name = UniqueUsername.build_key_name(username)
        entity = UniqueUsername.get_by_key_name(key_name)
        if clock is None:
            clock = datetime.datetime
        return entity is None or not entity._is_in_holding(clock.utcnow())

    def _is_in_holding(self, utcnow):
        return self.release_date + UniqueUsername.HOLDING_PERIOD_DELTA >= utcnow

    INFINITELY_FAR_FUTURE = datetime.datetime(9999, 1, 1, 0, 0, 0)

    # Released usernames are held for 120 days
    HOLDING_PERIOD_DELTA = datetime.timedelta(120)

    @staticmethod
    def _claim_internal(desired_name, claimer_id=None, clock=None):
        key_name = UniqueUsername.build_key_name(desired_name)
        if not UniqueUsername.is_valid_username(desired_name, key_name):
            return False

        is_available = UniqueUsername.is_available_username(
                desired_name, key_name, clock)
        if is_available:
            entity = UniqueUsername(key_name=key_name)
            entity.username = desired_name
            entity.release_date = UniqueUsername.INFINITELY_FAR_FUTURE
            entity.claimer_id = claimer_id
            entity.put()
        return is_available

    @staticmethod
    def claim(desired_name, claimer_id=None, clock=None):
        """ Claim an unclaimed username.

        Return True on success, False if you are a slow turtle or invalid.
        See is_valid_username for limitations of a username.

        """

        key_name = UniqueUsername.build_key_name(desired_name)
        if not UniqueUsername.is_valid_username(desired_name, key_name):
            return False

        return db.run_in_transaction(UniqueUsername._claim_internal,
                                     desired_name,
                                     claimer_id,
                                     clock)

    @staticmethod
    def release(username, clock=None):
        if clock is None:
            clock = datetime.datetime

        if username is None:
            logging.error("Trying to release a null username!")
            return

        entity = UniqueUsername.get_canonical(username)
        if entity is None:
            logging.warn("Releasing username %s that doesn't exist" % username)
            return
        entity.release_date = clock.utcnow()
        entity.put()
        
    @staticmethod
    def transfer(from_user, to_user):
        """ Transfers a username from one user to another, assuming the to_user
        does not already have a username.
        
        Returns whether or not a transfer occurred.

        """
        def txn():
            if not from_user.username or to_user.username:
                return False
            entity = UniqueUsername.get_canonical(from_user.username)
            entity.claimer_id = to_user.user_id
            to_user.username = from_user.username
            from_user.username = None
            db.put([from_user, to_user, entity])
            return True
        return util.ensure_in_transaction(txn, xg_on=True)

    @staticmethod
    def get_canonical(username):
        """ Returns the entity with the canonical format of the user name, as
        it was originally claimed by the user, given a string that may include
        more or less period characters in it.
        e.g. "joe.smith" may actually translate to "joesmith"
        """
        key_name = UniqueUsername.build_key_name(username)
        return UniqueUsername.get_by_key_name(key_name)

class NicknameIndex(db.Model):
    """ Index entries to be able to search users by their nicknames.
    Each user may have multiple index entries, all pointing to the same user.
    These entries are expected to be direct children of UserData entities.

    These are created for fast user searches.
    """

    # The index string that queries can be matched again. Must be built out
    # using nicknames.build_index_strings
    index_value = db.StringProperty()

    @staticmethod
    def update_indices(user):
        """ Updates the indices for a user given her current nickname. """
        nickname = user.nickname
        index_strings = nicknames.build_index_strings(nickname)

        db.delete(NicknameIndex.entries_for_user(user))
        entries = [NicknameIndex(parent=user, index_value=s)
                   for s in index_strings]
        db.put(entries)

    @staticmethod
    def entries_for_user(user):
        """ Retrieves all index entries for a given user. """
        q = NicknameIndex.all()
        q.ancestor(user)
        return q.fetch(10000)

    @staticmethod
    def users_for_search(raw_query):
        """ Given a raw query string, retrieve a list of the users that match
        that query by returning a list of their entity's key values.

        The values are guaranteed to be unique.

        TODO: there is no ranking among the result set, yet
        TODO: extend API so that the query can have an optional single token
              that can be prefixed matched, for autocomplete purposes
        """

        q = NicknameIndex.all()
        q.filter("index_value =", nicknames.build_search_query(raw_query))
        return list(set([entry.parent_key() for entry in q]))

PRE_PHANTOM_EMAIL = "http://nouserid.khanacademy.org/pre-phantom-user-2"

# Demo user khanacademy.demo2@gmail.com is a coworker of khanacademy.demo@gmail.com
# khanacademy.demo@gmail.com is coach of a bunch of Khan staff and LASD staff, which is shared
# with users as a demo. Access to the demo is via /api/auth/token_to_session with
# oauth tokens for khanacademy.demo2@gmail.com supplied via secrets.py
COACH_DEMO_COWORKER_EMAIL = "khanacademy.demo2@gmail.com"

class UnverifiedUser(db.Model):
    """ Preliminary signup data, including an e-mail address that needs to be
    verified. """
    
    email = db.StringProperty()
    birthdate = db.DateProperty(indexed=False)

    # used as a token sent in an e-mail verification link.
    randstring = db.StringProperty(indexed=True)
    
    @staticmethod
    def get_or_insert_for_value(email, birthdate):
        return UnverifiedUser.get_or_insert(
                key_name=email,
                email=email,
                birthdate=birthdate,
                randstring=os.urandom(20).encode("hex"))

    @staticmethod
    def get_for_value(email):
        # Email is also used as the db key
        return UnverifiedUser.get_by_key_name(email)

    @staticmethod
    def get_for_token(token):
        return UnverifiedUser.all().filter("randstring =", token).get()

class UserData(GAEBingoIdentityModel, CredentialedUser, db.Model):
    # Canonical reference to the user entity. Avoid referencing this directly
    # as the fields of this property can change; only the ID is stable and
    # user_id can be used as a unique identifier instead.
    user = db.UserProperty()

    # Deprecated - this was used to represent the current e-mail address of the
    # user but is no longer relevant. Do not use - see user_id instead.
    current_user = db.UserProperty()

    # An opaque and uniquely identifying string for a user - this is stable
    # even if the user changes her e-mail.
    user_id = db.StringProperty()

    # A uniquely identifying string for a user. This is not stable and can
    # change if a user changes her e-mail. This is not actually always an
    # e-mail; for non-Google users, this can be a
    # URI like http://facebookid.khanacademy.org/1234
    user_email = db.StringProperty()

    # A human-readable name that will be user-configurable.
    # Do not read or modify this directly! Instead, use the nickname property
    # and update_nickname method
    user_nickname = db.StringProperty(indexed=False)

    # A globally unique user-specified username,
    # which will be used in URLS like khanacademy.org/profile/<username>
    username = db.StringProperty(default="")
    
    moderator = db.BooleanProperty(default=False)
    developer = db.BooleanProperty(default=False)

    # Account creation date in UTC
    joined = db.DateTimeProperty(auto_now_add=True)
    
    # Last login date in UTC. Note that this was incorrectly set, and could
    # have stale values (though is always non-empty) for users who have never
    # logged in prior to the launch of our own password based logins(2012-04-12)
    last_login = db.DateTimeProperty(indexed=False)

    # Whether or not user has been hellbanned from community participation
    # by a moderator
    discussion_banned = db.BooleanProperty(default=False)

    # Names of exercises in which the user is *explicitly* proficient
    proficient_exercises = object_property.StringListCompatTsvProperty()

    # Names of all exercises in which the user is proficient
    all_proficient_exercises = object_property.StringListCompatTsvProperty()

    suggested_exercises = object_property.StringListCompatTsvProperty()
    badges = object_property.StringListCompatTsvProperty() # All awarded badges
    need_to_reassess = db.BooleanProperty(indexed=False)
    points = db.IntegerProperty(default=0)
    total_seconds_watched = db.IntegerProperty(default=0)

    # A list of email values corresponding to the "user" property of the coaches
    # for the user. Note: that it may not be the current, active email
    coaches = db.StringListProperty()

    coworkers = db.StringListProperty()
    student_lists = db.ListProperty(db.Key)
    map_coords = db.StringProperty(indexed=False)
    videos_completed = db.IntegerProperty(default=-1)
    last_daily_summary = db.DateTimeProperty(indexed=False)
    last_badge_review = db.DateTimeProperty(indexed=False)
    last_activity = db.DateTimeProperty(indexed=False)
    start_consecutive_activity_date = db.DateTimeProperty(indexed=False)
    count_feedback_notification = db.IntegerProperty(default= -1, indexed=False)
    question_sort_order = db.IntegerProperty(default= -1, indexed=False)
    uservideocss_version = db.IntegerProperty(default=0, indexed=False)
    has_current_goals = db.BooleanProperty(default=False, indexed=False)

    # A list of badge names that the user has chosen to display publicly
    # Note that this list is not contiguous - it may have "holes" in it
    # indicated by the reserved string "__empty__"
    public_badges = object_property.TsvProperty()

    # The name of the avatar the user has chosen. See avatar.util_avatar.py
    avatar_name = db.StringProperty(indexed=False)

    # The user's birthday was only relatively recently collected (Mar 2012)
    # so older UserData may not have this information.
    birthdate = db.DateProperty(indexed=False)
    
    # The user's gender is optional, and only collected as of Mar 2012,
    # so older UserData may not have this information.
    gender = db.StringProperty(indexed=False)

    # Whether or not the user has indicated she wishes to have a public
    # profile (and can be searched, etc)
    is_profile_public = db.BooleanProperty(default=False, indexed=False)

    _serialize_blacklist = [
            "badges", "count_feedback_notification",
            "last_daily_summary", "need_to_reassess", "videos_completed",
            "moderator", "question_sort_order",
            "last_login", "user", "current_user", "map_coords",
            "user_nickname", "user_email",
            "seconds_since_joined", "has_current_goals", "public_badges",
            "avatar_name", "username", "is_profile_public",
            "credential_version", "birthdate", "gender",
            "conversion_test_hard_exercises",
            "conversion_test_easy_exercises",
    ]

    conversion_test_hard_exercises = set(['order_of_operations', 'graphing_points',
        'probability_1', 'domain_of_a_function', 'division_4',
        'ratio_word_problems', 'writing_expressions_1', 'ordering_numbers',
        'geometry_1', 'converting_mixed_numbers_and_improper_fractions'])
    conversion_test_easy_exercises = set(['counting_1', 'significant_figures_1', 'subtraction_1'])

    @property
    def nickname(self):
        """ Gets a human-friendly display name that the user can optionally set
        themselves. Will initially default to either the Facebook name or
        part of the user's e-mail.
        """

        # Note - we make a distinction between "None", which means the user has
        # never gotten or set their nickname, and the empty string, which means
        # the user has explicitly made an empty nickname
        if self.user_nickname is not None:
            return self.user_nickname

        return nicknames.get_default_nickname_for(self)

    def update_nickname(self, nickname=None):
        """ Updates the user's nickname and relevant indices and persists
        to the datastore.
        """
        if nickname is None:
            nickname = nicknames.get_default_nickname_for(self)
        new_name = nickname or ""

        # TODO: Fix this in a more systematic way
        # Ending script tags are special since we can put profile data in JSON
        # embedded inside an HTML. Until we can fix that problem in the jsonify
        # code, we temporarily disallow these as a stop gap.
        new_name = new_name.replace('</script>', '')
        if new_name != self.user_nickname:
            if nickname and not nicknames.is_valid_nickname(nickname):
                # The user picked a name, and it seems offensive. Reject it.
                return False

            self.user_nickname = new_name
            def txn():
                NicknameIndex.update_indices(self)
                self.put()
            util.ensure_in_transaction(txn, xg_on=True)
        return True

    @property
    def email(self):
        """ Unlike key_email below, this email property
        represents the user's current email address and
        can be displayed to users.
        """
        return self.user_email

    @property
    def key_email(self):
        """ key_email is an unchanging key that's used
        as a reference to this user in many old db entities.
        It will never change, and it does not represent the user's
        actual email. It is used as a key for db queries only. It
        should not be displayed to users -- for that, use the 'email'
        property.
        """
        return self.user.email()

    @property
    def badge_counts(self):
        return util_badges.get_badge_counts(self)

    @property
    def prettified_user_email(self):
        if self.is_facebook_user:
            return "_fb" + self.user_id[len(FACEBOOK_ID_PREFIX):]
        elif self.is_phantom:
            return "nouser"
        else:
            return "_em" + urllib.quote(self.user_email)

    @staticmethod
    def get_from_url_segment(segment):
        username_or_email = None

        if segment:
            segment = urllib.unquote(segment).decode('utf-8').strip()
            if segment.startswith("_fb"):
                username_or_email = segment.replace("_fb", FACEBOOK_ID_PREFIX)
            elif segment.startswith("_em"):
                username_or_email = segment.replace("_em", "")
            else:
                username_or_email = segment

        return UserData.get_from_username_or_email(username_or_email)

    @property
    def profile_root(self):
        root = "/profile/"

        if self.username:
            root += self.username
        else:
            root += self.prettified_user_email

        return root

    # Return data about the user that we'd like to track in MixPanel
    @staticmethod
    def get_analytics_properties(user_data):
        properties_list = []

        if not user_data:
            properties_list.append(("User Type", "New"))
        elif user_data.is_phantom:
            properties_list.append(("User Type", "Phantom"))
        else:
            properties_list.append(("User Type", "Logged In"))

        if user_data:
            properties_list.append(("User Points", user_data.points))
            properties_list.append(("User Videos", user_data.get_videos_completed()))
            properties_list.append(("User Exercises", len(user_data.all_proficient_exercises)))
            properties_list.append(("User Badges", len(user_data.badges)))
            properties_list.append(("User Video Time", user_data.total_seconds_watched))

        return properties_list

    @staticmethod
    @request_cache.cache()
    def current():
        user_id = util.get_current_user_id(bust_cache=True)
        email = user_id

        google_user = users.get_current_user()
        if google_user:
            email = google_user.email()

        if user_id:
            # Once we have rekeyed legacy entities,
            # we will be able to simplify this.
            return  UserData.get_from_user_id(user_id) or \
                    UserData.get_from_db_key_email(email) or \
                    UserData.insert_for(user_id, email)
        return None

    @staticmethod
    def pre_phantom():
        return UserData.insert_for(PRE_PHANTOM_EMAIL, PRE_PHANTOM_EMAIL)

    @property
    def is_facebook_user(self):
        return is_facebook_user_id(self.user_id)

    @property
    def is_phantom(self):
        return util.is_phantom_user(self.user_id)

    @property
    def is_demo(self):
        return self.user_email.startswith(COACH_DEMO_COWORKER_EMAIL)

    @property
    def is_pre_phantom(self):
        return PRE_PHANTOM_EMAIL == self.user_email

    @property
    def seconds_since_joined(self):
        return util.seconds_since(self.joined)

    @staticmethod
    @request_cache.cache_with_key_fxn(lambda user_id: "UserData_user_id:%s" % user_id)
    def get_from_user_id(user_id):
        if not user_id:
            return None

        query = UserData.all()
        query.filter('user_id =', user_id)
        query.order('-points') # Temporary workaround for issue 289

        return query.get()

    @staticmethod
    def get_from_user_input_email(email):
        if not email:
            return None

        query = UserData.all()
        query.filter('user_email =', email)
        query.order('-points') # Temporary workaround for issue 289

        return query.get()
    
    @staticmethod
    def get_all_for_user_input_email(email):
        if not email:
            return []

        query = UserData.all()
        query.filter('user_email =', email)
        return query

    @staticmethod
    def get_from_username(username):
        if not username:
            return None
        canonical_username = UniqueUsername.get_canonical(username)
        if not canonical_username:
            return None
        query = UserData.all()
        query.filter('username =', canonical_username.username)
        return query.get()

    @staticmethod
    def get_from_db_key_email(email):
        if not email:
            return None

        query = UserData.all()
        query.filter('user =', users.User(email))
        query.order('-points') # Temporary workaround for issue 289

        return query.get()

    @staticmethod
    def get_from_user(user):
        return UserData.get_from_db_key_email(user.email())

    @staticmethod
    def get_from_username_or_email(username_or_email):
        if not username_or_email:
            return None

        user_data = None

        if UniqueUsername.is_valid_username(username_or_email):
            user_data = UserData.get_from_username(username_or_email)
        else:
            user_data = UserData.get_possibly_current_user(username_or_email)

        return user_data

    # Avoid an extra DB call in the (fairly often) case that the requested email
    # is the email of the currently logged-in user
    @staticmethod
    def get_possibly_current_user(email):
        if not email:
            return None

        user_data_current = UserData.current()
        if user_data_current and user_data_current.user_email == email:
            return user_data_current
        return UserData.get_from_user_input_email(email) or UserData.get_from_user_id(email)

    @classmethod
    def key_for(cls, user_id):
        return "user_id_key_%s" % user_id

    @staticmethod
    def get_possibly_current_user_by_username(username):
        if not username:
            return None

        user_data_current = UserData.current()
        if user_data_current and user_data_current.username == username:
            return user_data_current

        return UserData.get_from_username(username)

    @staticmethod
    def insert_for(user_id, email, username=None, password=None, **kwds):
        """ Creates a user with the specified values, if possible, or returns
        an existing user if the user_id has been used by an existing user.
        
        Returns None if user_id or email values are invalid.

        """

        if not user_id or not email:
            return None

        # Make default dummy values for the ones that don't matter
        prop_values = {
            'moderator': False,
            'proficient_exercises': [],
            'suggested_exercises': [],
            'need_to_reassess': True,
            'points': 0,
            'coaches': [],
        }

        # Allow clients to override
        prop_values.update(**kwds)
        
        # Forcefully override with important items.
        user = users.User(email)
        key_name = UserData.key_for(user_id)
        for pname, pvalue in {
            'key_name': key_name,
            'user': user,
            'current_user': user,
            'user_id': user_id,
            'user_email': email,
            }.iteritems():
            if pname in prop_values:
                logging.warning("UserData creation about to override"
                                " specified [%s] value" % pname)
            prop_values[pname] = pvalue

        if username or password:
            # Username or passwords are separate entities.
            # That means we have to do this in multiple steps - make a txn.
            def create_txn():
                user_data = UserData.get_by_key_name(key_name)
                if user_data is None:
                    user_data = UserData(**prop_values)
                    # Both claim_username and set_password updates user_data
                    # and will call put() for us.
                    if username and not user_data.claim_username(username):
                        raise Rollback("username [%s] already taken" % username)
                    if password and user_data.set_password(password):
                        raise Rollback("invalid password for user")
                else:
                    logging.warning("Tried to re-make a user for key=[%s]" %
                                    key_name)
                return user_data

            xg_on = db.create_transaction_options(xg=True)
            user_data = db.run_in_transaction_options(xg_on, create_txn)

        else:
            # No username means we don't have to do manual transactions.
            # Note that get_or_insert is a transaction itself, and it can't
            # be nested in the above transaction.
            user_data = UserData.get_or_insert(**prop_values)

        if user_data and not user_data.is_phantom:
            # Record that we now have one more registered user
            if (datetime.datetime.now() - user_data.joined).seconds < 60:
                # Extra safety check against user_data.joined in case some
                # subtle bug results in lots of calls to insert_for for
                # UserData objects with existing key_names.
                user_counter.add(1)

        return user_data

    def consume_identity(self, new_user):
        """ Takes over another UserData's identity by updating this user's
        user_id, and other personal information with that of new_user's,
        assuming the new_user has never received any points.

        This is useful if this account is a phantom user with history
        and needs to be updated with a newly registered user's info, or some
        other similar situation.

        This method will fail if new_user has any points whatsoever,
        since we don't yet support migrating associated UserVideo
        and UserExercise objects.

        Returns whether or not the merge was successful.
        
        """
        
        if (new_user.points > 0):
            return False

        # Really important that we be mindful of people who have been added as
        # coaches - no good way to transfer that right now.
        if new_user.has_students():
            return False
    
        def txn():
            self.user_id = new_user.user_id
            self.current_user = new_user.current_user
            self.user_email = new_user.user_email
            self.user_nickname = new_user.user_nickname
            self.birthdate = new_user.birthdate
            self.gender = new_user.gender
            self.joined = new_user.joined
            if new_user.last_login:
                if self.last_login:
                    self.last_login = max(new_user.last_login, self.last_login)
                else:
                    self.last_login = new_user.last_login
            self.set_password_from_user(new_user)
            UniqueUsername.transfer(new_user, self)
            
            # TODO(benkomalo): update nickname and indices!
        
            if self.put():
                new_user.delete()
                return True
            return False

        result = util.ensure_in_transaction(txn, xg_on=True)
        if result:
            # Note that all of the updates to the above fields causes changes
            # to indices affected by each user. Since some of those are really
            # important (e.g. retrieving a user by user_id), it'd be dangerous
            # for a subsequent request to see stale indices. Force an apply()
            # of the HRD by doing a get()
            db.get(self.key())
            db.get(new_user.key())
        return result

    @staticmethod
    def get_visible_user(user, actor=None):
        """ Retrieve user for actor, in the style of O-Town, all or nothing.

        TODO(marcia): Sort out UserData and UserProfile visibility turf war
        """
        if actor is None:
            actor = UserData.current() or UserData.pre_phantom()

        if user and user.is_visible_to(actor):
            # Allow access to user's profile
            return user

        return None

    def delete(self):
        # Override delete(), so that we can log this severe event, and clean
        # up some statistics.
        logging.info("Deleting user data for %s with points %s" % (self.key_email, self.points))
        logging.info("Dumping user data for %s: %s" % (self.user_id, jsonify(self)))

        if not self.is_phantom:
            user_counter.add(-1)
        
        # TODO(benkomalo): handle cleanup of nickname indices!

        # Delegate to the normal implentation
        super(UserData, self).delete()

    def is_certain_to_be_thirteen(self):
        """ A conservative check that guarantees a user is at least 13 years
        old based on their login type.

        Note that even if someone is over 13, this can return False, but if
        this returns True, they're guaranteed to be over 13.
        """

        # Normal Gmail accounts and FB accounts require users be at least 13yo.
        if self.birthdate:
            return age_util.get_age(self.birthdate) >= 13
            
        email = self.email
        return (email.endswith("@gmail.com")
                or email.endswith("@googlemail.com")  # Gmail in Germany
                or email.endswith("@khanacademy.org")  # We're special
                or self.developer  # Really little kids don't write software
                or is_facebook_user_id(email))

    def get_or_insert_exercise(self, exercise, allow_insert=True):
        if not exercise:
            return None

        exid = exercise.name
        userExercise = UserExercise.get_by_key_name(exid, parent=self)

        if not userExercise:
            # There are some old entities lying around that don't have keys.
            # We have to check for them here, but once we have reparented and rekeyed legacy entities,
            # this entire function can just be a call to .get_or_insert()
            query = UserExercise.all(keys_only=True)
            query.filter('user =', self.user)
            query.filter('exercise =', exid)
            query.order('-total_done') # Temporary workaround for issue 289

            # In order to guarantee consistency in the HR datastore, we need to query
            # via db.get for these old, parent-less entities.
            key_user_exercise = query.get()
            if key_user_exercise:
                userExercise = UserExercise.get(str(key_user_exercise))

        if allow_insert and not userExercise:
            userExercise = UserExercise.get_or_insert(
                key_name=exid,
                parent=self,
                user=self.user,
                exercise=exid,
                exercise_model=exercise,
                streak=0,
                _progress=0.0,
                longest_streak=0,
                first_done=datetime.datetime.now(),
                last_done=None,
                total_done=0,
                _accuracy_model=AccuracyModel(),
                )

        return userExercise

    def reassess_from_graph(self, user_exercise_graph):
        all_proficient_exercises = user_exercise_graph.proficient_exercise_names()
        suggested_exercises = user_exercise_graph.suggested_exercise_names()

        is_changed = (all_proficient_exercises != self.all_proficient_exercises or
                      suggested_exercises != self.suggested_exercises)

        self.all_proficient_exercises = all_proficient_exercises
        self.suggested_exercises = suggested_exercises
        self.need_to_reassess = False

        return is_changed

    def reassess_if_necessary(self, user_exercise_graph=None):
        if not self.need_to_reassess or self.all_proficient_exercises is None:
            return False

        if user_exercise_graph is None:
            user_exercise_graph = UserExerciseGraph.get(self)

        return self.reassess_from_graph(user_exercise_graph)

    def is_proficient_at(self, exid, exgraph=None):
        self.reassess_if_necessary(exgraph)
        return (exid in self.all_proficient_exercises)

    def is_explicitly_proficient_at(self, exid):
        return (exid in self.proficient_exercises)

    def is_suggested(self, exid):
        self.reassess_if_necessary()
        return (exid in self.suggested_exercises)

    def get_coaches_data(self):
        """ Return list of coaches UserData.
        """
        coaches = []
        for key_email in self.coaches:
            user_data_coach = UserData.get_from_db_key_email(key_email)
            if user_data_coach:
                coaches.append(user_data_coach)
        return coaches

    def get_students_data(self):
        coach_email = self.key_email
        query = UserData.all().filter('coaches =', coach_email)
        students_data = [s for s in query.fetch(1000)]

        if coach_email.lower() != coach_email:
            students_set = set([s.key().id_or_name() for s in students_data])
            query = UserData.all().filter('coaches =', coach_email.lower())
            for student_data in query:
                if student_data.key().id_or_name() not in students_set:
                    students_data.append(student_data)
        return students_data

    def get_coworkers_data(self):
        return filter(lambda user_data: user_data is not None, \
                map(lambda coworker_email: UserData.get_from_db_key_email(coworker_email) , self.coworkers))

    def has_students(self):
        coach_email = self.key_email
        count = UserData.all().filter('coaches =', coach_email).count()

        if coach_email.lower() != coach_email:
            count += UserData.all().filter('coaches =', coach_email.lower()).count()

        return count > 0

    def remove_student_lists(self, removed_coach_emails):
        """ Remove student lists associated with removed coaches.
        """
        if len(removed_coach_emails):
            # Get the removed coaches' keys
            removed_coach_keys = frozenset([
                    UserData.get_from_username_or_email(coach_email).key()
                    for coach_email in removed_coach_emails])

            # Get the StudentLists from our list of StudentList keys
            student_lists = StudentList.get(self.student_lists)

            # Theoretically, a StudentList allows for multiple coaches,
            # but in practice there is exactly one coach per StudentList.
            # If/when we support multiple coaches per list, we would need to change
            # how this works... How *does* it work? Well, let me tell you.

            # Set our student_lists to all the keys of StudentLists
            # whose coaches do not include any removed coaches.
            self.student_lists = [l.key() for l in student_lists
                    if (len(frozenset(l.coaches) & removed_coach_keys) == 0)]

    def is_coached_by(self, user_data_coach):
        return user_data_coach.key_email in self.coaches or user_data_coach.key_email.lower() in self.coaches

    def is_coworker_of(self, user_data_coworker):
        return user_data_coworker.key_email in self.coworkers

    def is_coached_by_coworker_of_coach(self, user_data_coach):
        for coworker_email in user_data_coach.coworkers:
            if coworker_email in self.coaches:
                return True
        return False

    def is_administrator(self):
        # Only works for currently logged in user. Make sure there
        # is both a current user data and current user is an admin.
        user_data = UserData.current()
        return user_data and users.is_current_user_admin()

    def is_visible_to(self, user_data):
        """ Returns whether or not this user's information is *fully* visible
        to the specified user
        """
        return (self.key_email == user_data.key_email or self.is_coached_by(user_data)
                or self.is_coached_by_coworker_of_coach(user_data)
                or user_data.developer or user_data.is_administrator())

    def are_students_visible_to(self, user_data):
        return self.is_coworker_of(user_data) or user_data.developer or user_data.is_administrator()

    def record_activity(self, dt_activity):

        # Make sure last_activity and start_consecutive_activity_date have values
        self.last_activity = self.last_activity or dt_activity
        self.start_consecutive_activity_date = self.start_consecutive_activity_date or dt_activity

        if dt_activity > self.last_activity:

            # If it has been over 40 hours since we last saw this user, restart
            # the consecutive activity streak.
            #
            # We allow for a lenient 40 hours in order to offer kinder timezone
            # interpretation.
            #
            # 36 hours wasn't quite enough. A user with activity at 8am on
            # Monday and 8:15pm on Tuesday would not have consecutive days of
            # activity.
            #
            # See http://meta.stackoverflow.com/questions/55483/proposed-consecutive-days-badge-tracking-change
            if util.hours_between(self.last_activity, dt_activity) >= 40:
                self.start_consecutive_activity_date = dt_activity

            self.last_activity = dt_activity

    def current_consecutive_activity_days(self):
        if not self.last_activity or not self.start_consecutive_activity_date:
            return 0

        dt_now = datetime.datetime.now()

        # If it has been over 40 hours since last activity, bail.
        if util.hours_between(self.last_activity, dt_now) >= 40:
            return 0

        return (self.last_activity - self.start_consecutive_activity_date).days

    def add_points(self, points):
        if self.points is None:
            self.points = 0

        if not hasattr(self, "_original_points"):
            self._original_points = self.points

        # Check if we crossed an interval of 2500 points
        if self.points % 2500 > (self.points + points) % 2500:
            util_notify.update(self, user_exercise=None, threshold=True)
        self.points += points

    def original_points(self):
        return getattr(self, "_original_points", 0)

    def get_videos_completed(self):
        if self.videos_completed < 0:
            self.videos_completed = UserVideo.count_completed_for_user_data(self)
            self.put()
        return self.videos_completed

    def feedback_notification_count(self):
        if self.count_feedback_notification == -1:
            self.count_feedback_notification = models_discussion.FeedbackNotification.gql("WHERE user = :1", self.user).count()
            self.put()
        return self.count_feedback_notification

    def save_goal(self, goal):
        '''save a goal, atomically updating the user_data.has_current_goal when
        necessary'''

        if self.has_current_goals: # no transaction necessary
            goal.put()
            return

        # otherwise this is the first goal the user has created, so be sure we
        # update user_data.has_current_goals too
        def save_goal():
            self.has_current_goals = True
            db.put([self, goal])
        db.run_in_transaction(save_goal)

    def claim_username(self, name, clock=None):
        """ Claims a username for the current user, and assigns it to her
        atomically. Returns True on success.
        """
        def claim_and_set():
            claim_success = UniqueUsername._claim_internal(name,
                                                           claimer_id=self.user_id,
                                                           clock=clock)
            if claim_success:
                if self.username:
                    UniqueUsername.release(self.username, clock)
                self.username = name
                self.put()
            return claim_success
        
        result = util.ensure_in_transaction(claim_and_set, xg_on=True)
        if result:
            # Success! Ensure we flush the apply() phase of the modifications
            # so that subsequent queries get consistent results. This makes
            # claiming usernames slightly slower, but safer since rapid
            # claiming or rapid claim/read won't result in weirdness.
            db.get([self.key()])
        return result

    def has_password(self):
        return self.credential_version is not None

    def has_public_profile(self):
        return (self.is_profile_public
                and self.username is not None
                and len(self.username) > 0)

    def __unicode__(self):
        return "<UserData [%s] [%s] [%s]>" % (self.user_id,
                                              self.email,
                                              self.username or "<no username>")

    @classmethod
    def from_json(cls, json, user=None):
        '''This method exists for testing convenience only. It's called only
        by code that runs in exclusively in development mode. Do not rely on
        this method in production code. If you need to break this code to
        implement some new feature, feel free!
        '''
        user_id = json['user_id']
        email = json['email']
        user = user or users.User(email)

        user_data = cls(
            key_name=cls.key_for(user_id),
            user=user,
            current_user=user,
            user_id=user_id,
            user_email=email,
            moderator=False,
            joined=util.parse_iso8601(json['joined']),
            last_activity=util.parse_iso8601(json['last_activity']),
            last_badge_review=util.parse_iso8601(json['last_badge_review']),
            start_consecutive_activity_date=util.parse_iso8601(json['start_consecutive_activity_date']),
            need_to_reassess=True,
            points=int(json['points']),
            nickname=json['nickname'],
            coaches=['test@example.com'],
            total_seconds_watched=int(json['total_seconds_watched']),
            all_proficient_exercises=json['all_proficient_exercises'],
            proficient_exercises=json['proficient_exercises'],
            suggested_exercises=json['suggested_exercises'],
        )
        return user_data

class TopicVersion(db.Model):
    created_on = db.DateTimeProperty(indexed=False, auto_now_add=True)
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)
    made_default_on = db.DateTimeProperty(indexed=False)
    copied_from = db.SelfReferenceProperty(indexed=False)
    last_edited_by = db.UserProperty(indexed=False)
    number = db.IntegerProperty(required=True)
    title = db.StringProperty(indexed=False)
    description = db.StringProperty(indexed=False)
    default = db.BooleanProperty(default=False)
    edit = db.BooleanProperty(default=False)

    _serialize_blacklist = ["copied_from"]

    @property
    def copied_from_number(self):
        if self.copied_from:
            return self.copied_from.number

    @staticmethod
    def get_by_id(version_id):
        if version_id is None or version_id == "default":
            return TopicVersion.get_default_version()
        if version_id == "edit":
            return TopicVersion.get_edit_version()
        number = int(version_id)
        return TopicVersion.all().filter("number =", number).get()

    @staticmethod
    def get_by_number(number):
        return TopicVersion.all().filter("number =", number).get()

    # used by get_unused_content - gets expunged by cache to frequently (when people are updating content, while this should only change when content is added)
    @staticmethod
    @layer_cache.cache_with_key_fxn(lambda :
        "TopicVersion.get_all_content_keys_%s" %
        Setting.cached_content_add_date(),
        layer=layer_cache.Layers.Memcache)
    def get_all_content_keys():
        video_keys = Video.all(keys_only=True).fetch(100000)
        exercise_keys = Exercise.all(keys_only=True).fetch(100000)
        url_keys = Url.all(keys_only=True).fetch(100000)

        content = video_keys
        content.extend(exercise_keys)
        content.extend(url_keys)
        return content

    def get_unused_content(self):
        topics = Topic.all().filter("version =", self).run()
        used_content_keys = set()
        for t in topics:
            used_content_keys.update([c for c in t.child_keys if c.kind() != "Topic"])

        content_keys = set(TopicVersion.get_all_content_keys())

        return db.get(content_keys - used_content_keys)


    @staticmethod
    def get_latest_version():
        return TopicVersion.all().order("-number").get()

    @staticmethod
    def get_latest_version_number():
        latest_version = TopicVersion.all().order("-number").get()
        return latest_version.number if latest_version else 0

    @staticmethod
    def create_new_version():
        new_version_number = TopicVersion.get_latest_version_number() + 1
        if UserData.current():
            last_edited_by = UserData.current().user
        else:
            last_edited_by = None
        new_version = TopicVersion(last_edited_by=last_edited_by,
                                   number=new_version_number)
        new_version.put()
        return new_version

    @staticmethod
    def get_default_version():
        return TopicVersion.all().filter("default = ", True).get()

    @staticmethod
    def get_edit_version():
        return TopicVersion.all().filter("edit = ", True).get()

    @staticmethod
    @synchronized_with_memcache(timeout=300) #takes 70secs on dev 03/2012
    def create_edit_version():
        version = TopicVersion.all().filter("edit = ", True).get()
        if version is None:
            default = TopicVersion.get_default_version()
            version = default.copy_version()
            version.edit = True
            version.put()
            return version
        else:
            logging.warning("Edit version already exists")
            return False

    def copy_version(self):
        version = TopicVersion.create_new_version()

        old_root = Topic.get_root(self)
        old_tree = old_root.make_tree(types=["Topics"], include_hidden=True)
        TopicVersion.copy_tree(old_tree, version)

        version.copied_from = self
        version.put()

        return version

    @staticmethod
    def copy_tree(old_tree, new_version, new_root=None, parent=None):
        parent_keys = []
        ancestor_keys = []
        if parent:
            parent_keys = [parent.key()]
            ancestor_keys = parent_keys[:]
            ancestor_keys.extend(parent.ancestor_keys)

        if new_root:
            key_name = old_tree.key().name()
        else:
            #don't copy key_name of root as it is parentless, and needs its own key
            key_name = Topic.get_new_key_name()

        new_tree = util.clone_entity(old_tree,
                                     key_name=key_name,
                                     version=new_version,
                                     parent=new_root,
                                     parent_keys=parent_keys,
                                     ancestor_keys=ancestor_keys)
        new_tree.put()
        if not new_root:
            new_root = new_tree

        old_key_new_key_dict = {}
        for child in old_tree.children:
            old_key_new_key_dict[child.key()] = TopicVersion.copy_tree(child, new_version, new_root, new_tree).key()

        new_tree.child_keys = [c if c not in old_key_new_key_dict else old_key_new_key_dict[c] for c in old_tree.child_keys]
        new_tree.put()
        return new_tree

    def update(self):
        if UserData.current():
            last_edited_by = UserData.current().user
        else:
            last_edited_by = None
        self.last_edited_by = last_edited_by
        self.put()

    def find_content_problems(self):
        logging.info("checking for problems")
        version = self

        # find exercises that are overlapping on the knowledge map
        logging.info("checking for exercises that are overlapping on the knowledge map")
        exercises = Exercise.all()
        exercise_dict = dict((e.key(),e) for e in exercises)

        location_dict = {}
        duplicate_positions = list()
        changes = VersionContentChange.get_updated_content_dict(version)
        exercise_changes = dict((k,v) for k,v in changes.iteritems()
                                if v.key() in exercise_dict)
        exercise_dict.update(exercise_changes)

        for exercise in [e for e in exercise_dict.values()
                         if e.live and not e.summative]:

            if exercise.h_position not in location_dict:
                location_dict[exercise.h_position] = {}

            if exercise.v_position in location_dict[exercise.h_position]:
                location_dict[exercise.h_position][exercise.v_position].append(exercise)
                duplicate_positions.append(
                    location_dict[exercise.h_position][exercise.v_position])
            else:
                location_dict[exercise.h_position][exercise.v_position] = [exercise]

        # find videos whose duration is 0
        logging.info("checking for videos with 0 duration")
        zero_duration_videos = Video.all().filter("duration =", 0).fetch(10000)
        zero_duration_dict = dict((v.key(),v) for v in zero_duration_videos)
        video_changes = dict((k,v) for k,v in changes.iteritems()
                                if k in zero_duration_dict or (
                                type(v) == Video and v.duration == 0))
        zero_duration_dict.update(video_changes)
        zero_duration_videos = [v for v in zero_duration_dict.values()
                                if v.duration == 0]

        # find videos with invalid youtube_ids that would be marked live
        logging.info("checking for videos with invalid youtube_ids")
        root = Topic.get_root(version)
        videos = root.get_videos(include_descendants = True)
        bad_videos = []
        for video in videos:
            if re.search("_DUP_\d*$", video.youtube_id):
                bad_videos.append(video)

        problems = {
            "ExerciseVideos with topicless videos" :
                ExerciseVideo.get_all_with_topicless_videos(version),
            "Exercises with colliding positions" : list(duplicate_positions),
            "Zero duration videos": zero_duration_videos,
            "Videos with bad youtube_ids": bad_videos}

        return problems

    def set_default_version(self):
        logging.info("starting set_default_version")
        Setting.topic_admin_task_message("Publish: started")
        run_code = base64.urlsafe_b64encode(os.urandom(30))
        do_set_default_deferred_step(check_for_problems,
                            self.number,
                            run_code)

def do_set_default_deferred_step(func, version_number, run_code):
    taskname = "v%i_run_%s_%s" % (version_number, run_code, func.__name__)
    try:
        deferred.defer(func,
                       version_number,
                       run_code,
                       _queue = "topics-set-default-queue",
                       _name = taskname,
                       _url = "/_ah/queue/deferred_topics-set-default-queue")
    except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
        logging.info("deferred task %s already exists" % taskname)

def check_for_problems(version_number, run_code):
    Setting.topic_admin_task_message("Publish: checking for content problems")
    version = TopicVersion.get_by_id(version_number)
    content_problems = version.find_content_problems()
    for problem_type, problems in content_problems.iteritems():
        if len(problems):
            content_problems["Version"] = version_number
            content_problems["Date detected"] = datetime.datetime.now()
            layer_cache.KeyValueCache.set(
                "set_default_version_content_problem_details", content_problems)
            Setting.topic_admin_task_message(("Error - content problems " +
                "found: %s. <a target=_blank " +
                "href='/api/v1/dev/topictree/problems'>" +
                "Click here to see problems.</a>") %
                (problem_type))

            raise deferred.PermanentTaskFailure

    do_set_default_deferred_step(apply_version_content_changes,
                                 version_number,
                                 run_code)

def apply_version_content_changes(version_number, run_code):
    Setting.topic_admin_task_message("Publish: applying version content changes")
    version = TopicVersion.get_by_id(version_number)
    changes = VersionContentChange.all().filter('version =', version).fetch(10000)
    changes = util.prefetch_refprops(changes, VersionContentChange.content)
    num_changes = len(changes)
    for i, change in enumerate(changes):
        change.apply_change()
        logging.info("applied change %i of %i" % (i, num_changes))
    logging.info("applied content changes")
    do_set_default_deferred_step(preload_default_version_data,
                                 version_number,
                                 run_code)

def preload_default_version_data(version_number, run_code):
    Setting.topic_admin_task_message("Publish: preloading cache")
    version = TopicVersion.get_by_id(version_number)

    # Causes circular importing if put at the top
    from library import library_content_html
    import autocomplete
    import templatetags
    from knowledgemap.layout import MapLayout

    # Preload library for upcoming version
    library_content_html(False, version.number)
    logging.info("preloaded library_content_html")

    library_content_html(True, version.number)
    logging.info("preloaded ajax library_content_html")

    # Preload autocomplete cache
    autocomplete.video_title_dicts(version.number)
    logging.info("preloaded video autocomplete")

    autocomplete.topic_title_dicts(version.number)
    logging.info("preloaded topic autocomplete")

    # Preload topic pages
    for topic in Topic.get_all_topics(version=version):
        topic.get_topic_page_json()
    logging.info("preloaded topic pages")

    # Preload topic browser
    templatetags.topic_browser("browse", version.number)
    templatetags.topic_browser("browse-fixed", version.number)
    templatetags.topic_browser_data(version_number=version.number, show_topic_pages=False)
    templatetags.topic_browser_data(version_number=version.number, show_topic_pages=True)
    logging.info("preloaded topic_browsers")

    # Sync all topic exercise badges with upcoming version
    topic_exercise_badges.sync_with_topic_version(version)
    logging.info("synced topic exercise badges")

    map_layout = MapLayout.get_for_version(version)
    if not map_layout.has_layout:
        # Copy the previous maplayout to current version's maplayout
        # if it doesn't already exist.
        # TODO: this is temporary. Eventually this should be generated correctly,
        # once the topics admin UI can send maplayout info.

        previous_version = TopicVersion.get_by_id(version.copied_from_number)
        map_layout_previous = MapLayout.get_for_version(previous_version)

        if not map_layout_previous.has_layout:
            Setting.topic_admin_task_message("Error - missing map layout and no previous version to copy from.")
            raise deferred.PermanentTaskFailure

        map_layout.layout = map_layout_previous.layout
        map_layout.put()

    do_set_default_deferred_step(change_default_version,
                                 version_number,
                                 run_code)

def change_default_version(version_number, run_code):
    Setting.topic_admin_task_message("Publish: changing default version")
    version = TopicVersion.get_by_id(version_number)

    default_version = TopicVersion.get_default_version()

    def update_txn():

        if default_version:
            default_version.default = False
            default_version.put()

        version.default = True
        version.made_default_on = datetime.datetime.now()
        version.edit = False

        Setting.topic_tree_version(version.number)
        Setting.cached_content_add_date(datetime.datetime.now())

        version.put()

    # using --high-replication is slow on dev, so instead not using cross-group transactions on dev
    if App.is_dev_server:
        update_txn()
    else:
        xg_on = db.create_transaction_options(xg=True)
        db.run_in_transaction_options(xg_on, update_txn)
        # setting the topic tree version in the transaction won't update
        # memcache as the new values for the setting are not complete till the
        # transaction finishes ... so updating again outside the txn
        Setting.topic_tree_version(version.number)

    logging.info("done setting new default version")

    Setting.topic_admin_task_message("Publish: reindexing new content")

    Topic.reindex(version)
    logging.info("done fulltext reindexing topics")

    Setting.topic_admin_task_message("Publish: creating new edit version")

    TopicVersion.create_edit_version()
    logging.info("done creating new edit version")

    # update the new number of videos on the homepage
    vids = Video.get_all_live()
    urls = Url.get_all_live()
    Setting.count_videos(len(vids) + len(urls))
    Video.approx_count(bust_cache=True)

    do_set_default_deferred_step(rebuild_content_caches,
                                 version_number,
                                 run_code)

def rebuild_content_caches(version_number, run_code):
    """ Uses existing Topic structure to rebuild and recache topic_string_keys
    properties in Video, Url, and Exercise entities for easy parental Topic
    lookups.
    """
    Setting.topic_admin_task_message("Publish: rebuilding content caches")

    version = TopicVersion.get_by_id(version_number)

    topics = Topic.get_all_topics(version)  # does not include hidden topics!

    videos = [v for v in Video.all()]
    video_dict = dict((v.key(), v) for v in videos)

    for video in videos:
        video.topic_string_keys = []

    urls = [u for u in Url.all()]
    url_dict = dict((u.key(), u) for u in urls)

    for url in urls:
        url.topic_string_keys = []

    # Grab all Exercise objects, even those that are hidden
    exercises = list(Exercise.all_unsafe())
    exercise_dict = dict((e.key(), e) for e in exercises)

    for exercise in exercises:
        exercise.topic_string_keys = []

    found_videos = 0

    for topic in topics:

        logging.info("Rebuilding content cache for topic " + topic.title)
        topic_key_str = str(topic.key())

        for child_key in topic.child_keys:

            if child_key.kind() == "Video":

                if child_key in video_dict:
                    video_dict[child_key].topic_string_keys.append(topic_key_str)
                    found_videos += 1
                else:
                    logging.info("Failed to find video " + str(child_key))

            elif child_key.kind() == "Url":

                if child_key in url_dict:
                    url_dict[child_key].topic_string_keys.append(topic_key_str)
                    found_videos += 1
                else:
                    logging.info("Failed to find URL " + str(child_key))

            elif child_key.kind() == "Exercise":

                if child_key in exercise_dict:
                    exercise_dict[child_key].topic_string_keys.append(topic_key_str)
                else:
                    logging.info("Failed to find exercise " + str(child_key))

    Setting.topic_admin_task_message("Publish: putting all content caches")
    logging.info("About to put content caches for all videos, urls, and exercises.")
    db.put(list(videos) + list(urls) + list(exercises))
    logging.info("Finished putting videos, urls, and exercises.")

    # Wipe the Exercises cache key
    Setting.cached_exercises_date(str(datetime.datetime.now()))

    logging.info("Rebuilt content topic caches. (" + str(found_videos) + " videos)")
    logging.info("set_default_version complete")
    Setting.topic_admin_task_message("Publish: finished successfully")

class VersionContentChange(db.Model):
    """ This class keeps track of changes made in the admin/content editor
    The changes will be applied when the version is set to default
    """

    version = db.ReferenceProperty(TopicVersion, collection_name="changes")
    # content is the video/exercise/url that has been changed
    content = db.ReferenceProperty()
    # indexing updated_on as it may be needed for rolling back
    updated_on = db.DateTimeProperty(auto_now=True)
    last_edited_by = db.UserProperty(indexed=False)
    # content_changes is a dict of the properties that have been changed
    content_changes = object_property.UnvalidatedObjectProperty()

    def put(self):
        last_edited_by = UserData.current().user if UserData.current() else None
        self.last_edited_by = last_edited_by
        db.Model.put(self)

    def apply_change(self):
        # exercises imports from request_handler which imports from models,
        # meaning putting this import at the top creates a import loop
        from exercises import UpdateExercise
        content = self.updated_content()
        content.put()

        if (content.key().kind() == "Exercise"
            and hasattr(content, "related_videos")):
            UpdateExercise.do_update_related_videos(content,
                                                    content.related_videos)

        return content

    # if content is passed as an argument it saves a reference lookup
    def updated_content(self, content=None):
        if content is None:
            content = self.content
        elif content.key() != self.content.key():
            raise Exception("key of content passed in does not match self.content")

        for prop, value in self.content_changes.iteritems():
            try:
                setattr(content, prop, value)
            except AttributeError:
                logging.info("cant set %s on a %s" % (prop, content.__class__.__name__))

        return content

    @staticmethod
    @request_cache.cache()
    def get_updated_content_dict(version):
        query = VersionContentChange.all().filter("version =", version)
        return dict((c.key(), c) for c in
                    [u.updated_content(u.content) for u in query])

    @staticmethod
    def get_change_for_content(content, version):
        query = VersionContentChange.all().filter("version =", version)
        query.filter("content =", content)
        change = query.get()

        if change:
            # since we have the content already, updating the property may save
            # a reference lookup later
            change.content = content

        return change

    @staticmethod
    def add_new_content(klass, version, new_props, changeable_props=None,
                        put_change=True):
        filtered_props = dict((str(k), v) for k,v in new_props.iteritems()
                         if changeable_props is None or k in changeable_props)
        content = klass(**filtered_props)
        content.put()

        if (type(content) == Exercise and "related_videos" in new_props):
            # exercises imports from request_handler which imports from models,
            # meaning putting this import at the top creates a import loop
            from exercises import UpdateExercise

            if "related_video_keys" in new_props:
                related_video_keys = new_props["related_video_keys"]
                logging.info("related video keys already added")
            else:
                related_video_keys = []
                for readable_id in new_props["related_videos"]:
                    video = Video.get_for_readable_id(readable_id, version)
                    logging.info("doing get for readable_id")
                    related_video_keys.append(video.key())

            for i, video_key in enumerate(related_video_keys):
                ExerciseVideo(
                    exercise=content,
                    video=video_key,
                    exercise_order=i
                    ).put()

        if put_change:
            change = VersionContentChange(parent=version)
            change.version = version
            change.content_changes = filtered_props
            change.content = content
            Setting.cached_content_add_date(datetime.datetime.now())
            change.put()
        return content

    @staticmethod
    def add_content_change(content, version, new_props, changeable_props=None):
        if changeable_props is None:
            changeable_props = new_props.keys()

        change = VersionContentChange.get_change_for_content(content, version)

        if change:
            previous_changes = True
        else:
            previous_changes = False
            change = VersionContentChange(parent=version)
            change.version = version
            change.content = content

        change.content_changes = {}

        if content and content.is_saved():

            for prop in changeable_props:
                if (prop in new_props and
                    new_props[prop] is not None and (
                        not hasattr(content, prop) or (
                            prop != "related_videos" and
                            new_props[prop] != getattr(content, prop)
                        ) or (
                            prop == "related_videos" and
                            set(new_props[prop]) != set(getattr(content, prop))
                        ))
                    ):

                    # add new changes for all props that are different from what
                    # is currently in content
                    change.content_changes[prop] = new_props[prop]
        else:
            raise Exception("content does not exit yet, call add_new_content instead")

        # only put the change if we have actually changed any props
        if change.content_changes:
            change.put()

        # delete the change if we are back to the original values
        elif previous_changes:
            change.delete()

        return change.content_changes

class Topic(Searchable, db.Model):
    title = db.StringProperty(required=True) # title used when viewing topic in a tree structure
    standalone_title = db.StringProperty() # title used when on its own
    id = db.StringProperty(required=True) # this is the slug, or readable_id - the one used to refer to the topic in urls and in the api
    extended_slug = db.StringProperty(indexed=False) # this is the URI path for this topic, i.e. "math/algebra"
    description = db.TextProperty(indexed=False)
    parent_keys = db.ListProperty(db.Key) # to be able to access the parent without having to resort to a query - parent_keys is used to be able to hold more than one parent if we ever want that
    ancestor_keys = db.ListProperty(db.Key) # to be able to quickly get all descendants
    child_keys = db.ListProperty(db.Key) # having this avoids having to modify Content entities
    version = db.ReferenceProperty(TopicVersion, required=True)
    tags = db.StringListProperty()
    hide = db.BooleanProperty(default=False)
    created_on = db.DateTimeProperty(indexed=False, auto_now_add=True)
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)
    last_edited_by = db.UserProperty(indexed=False)
    INDEX_ONLY = ['standalone_title', 'description']
    INDEX_TITLE_FROM_PROP = 'standalone_title'
    INDEX_USES_MULTI_ENTITIES = False

    _serialize_blacklist = ["child_keys", "version", "parent_keys", "ancestor_keys", "created_on", "updated_on", "last_edited_by"]
    # the ids of the topic on the homepage in which we will display their first
    # level child topics
    _super_topic_ids = ["algebra", "arithmetic", "art-history", "geometry", 
                        "brit-cruise", "california-standards-test", "gmat",
                        "linear-algebra"]

    @property
    def relative_url(self):
        return '/#%s' % self.id

    @property
    def topic_page_url(self):
         return '/%s' % self.get_extended_slug()

    @property
    def ka_url(self):
        return util.absolute_url(self.relative_url)

    def get_visible_data(self, node_dict=None):
        if node_dict:
            children = [ node_dict[c] for c in self.child_keys if c in node_dict ]
        else:
            children = db.get(self.child_keys)

        if not self.version.default:
            updates = VersionContentChange.get_updated_content_dict(self.version)
            children = [c if c.key() not in updates else updates[c.key()]
                        for c in children]

        self.children = []
        for child in children:
            self.children.append({
				"kind": child.__class__.__name__,
				"id": getattr(child, "id", getattr(child, "readable_id", getattr(child, "name", child.key().id()))),
				"title": getattr(child, "title", getattr(child, "display_name", "")),
				"hide": getattr(child, "hide", False),
				"url": getattr(child, "ka_url", getattr(child, "url", ""))
			})
        return self

    def get_library_data(self, node_dict=None):
        from homepage import thumbnail_link_dict

        if node_dict:
            children = [ node_dict[c] for c in self.child_keys if c in node_dict ]
        else:
            children = db.get(self.child_keys)

        (thumbnail_video, thumbnail_topic) = self.get_first_video_and_topic()

        ret = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "children": [{
                "url": "/%s/v/%s" % (self.get_extended_slug(), v.readable_id),
                "key_id": v.key().id(),
                "title": v.title
            } for v in children if v.__class__.__name__ == "Video"],
            "child_count": len([v for v in children if v.__class__.__name__ == "Video"]),
            "thumbnail_link": thumbnail_link_dict(video=thumbnail_video, parent_topic=thumbnail_topic),
        }

        return ret

    @layer_cache.cache_with_key_fxn(lambda self:
        "topic_get_topic_page_json_%s_v1" % self.key(),
        layer=layer_cache.Layers.InAppMemory | layer_cache.Layers.Memcache | layer_cache.Layers.Datastore)
    def get_topic_page_json(self):
        from homepage import thumbnail_link_dict

        (marquee_video, subtopic) = self.get_first_video_and_topic()

        tree = self.make_tree(types=["Video"])

        # If there are child videos, child topics are ignored.
        # There is no support for mixed topic/video containers.
        video_child_keys = [v for v in self.child_keys if v.kind() == "Video"]
        if not video_child_keys:
            # Fetch child topics
            topic_child_keys = [t for t in self.child_keys if t.kind() == "Topic"]
            topic_children = filter(lambda t: t.has_children_of_type(["Video"]),
                                    db.get(topic_child_keys))

            # Fetch the descendent videos
            node_keys = []
            for subtopic in topic_children:
                videos = filter(lambda v: v.kind() == "Video", subtopic.child_keys)
                if videos:
                    node_keys.extend(videos)

            nodes = db.get(node_keys)
            node_dict = dict((node.key(), node) for node in nodes)

            # Get the subtopic video data
            subtopics = [t.get_library_data(node_dict=node_dict) for t in topic_children]
            child_videos = None
        else:
            # Fetch the child videos
            nodes = db.get(video_child_keys)
            node_dict = dict((node.key(), node) for node in nodes)

            # Get the topic video data
            subtopics = None
            child_videos = self.get_library_data(node_dict=node_dict)

        topic_info = {
            "topic": self,
            "marquee_video": thumbnail_link_dict(video=marquee_video, parent_topic=subtopic),
            "subtopics": subtopics,
            "child_videos": child_videos,
            "extended_slug": self.get_extended_slug(),
        }

        return jsonify(topic_info, camel_cased=True)

    def get_child_order(self, child_key):
        return self.child_keys.index(child_key)

    def has_content(self):
        for child_key in self.child_keys:
            if child_key.kind() != "Topic":
                return True
        return False

    def has_children_of_type(self, types):
        """ Return true if this Topic has at least one child of
        any of the passed in types.

        Types should be an array of type strings:
            has_children_of_type(["Topic", "Video"])
        """
        return any(child_key.kind() in types for child_key in self.child_keys)

    # Gets the slug path of this topic, including parents, i.e. math/arithmetic/fractions
    def get_extended_slug(self):
        if self.extended_slug:
            return self.extended_slug

        parent_ids = [topic.id for topic in db.get(self.ancestor_keys)]
        parent_ids.reverse()
        if len(parent_ids) > 1:
            slug = "%s/%s" % ('/'.join(parent_ids[1:]), self.id)
        else:
            slug = self.id

        self.extended_slug = slug
        self.put()

        return slug

    # Gets the data we need for the video player
    @layer_cache.cache_with_key_fxn(lambda self:
        "topic_get_play_data_%s" % self.key(),
        layer=layer_cache.Layers.Memcache)
    def get_play_data(self):

        # Find last video in the previous topic
        previous_video = None
        previous_video_topic = None
        previous_topic = self

        while not previous_video:
            previous_topic = previous_topic.get_previous_topic()
            # Don't iterate past the end of the current top-level topic
            if previous_topic and len(previous_topic.ancestor_keys) > 1:
                (previous_video, previous_video_topic) = previous_topic.get_last_video_and_topic()
            else:
                break

        # Find first video in the next topic
        next_video = None
        next_video_topic = None
        next_topic = self

        while not next_video:
            next_topic = next_topic.get_next_topic()
            # Don't iterate past the end of the current top-level topic
            if next_topic and len(next_topic.ancestor_keys) > 1:
                (next_video, next_video_topic) = next_topic.get_first_video_and_topic()
            else:
                break

        # List all the videos in this topic
        videos_dict = [{
            "readable_id": v.readable_id,
            "key_id": v.key().id(),
            "title": v.title
        } for v in Topic.get_cached_videos_for_topic(self)]

        ancestor_topics = [{
            "title": topic.title, 
            "url": (topic.topic_page_url if topic.id in Topic._super_topic_ids 
                    or topic.has_content() else None)
            }
            for topic in db.get(self.ancestor_keys)][0:-1]
        ancestor_topics.reverse()

        return {
            'id': self.id,
            'title': self.title,
            'url': self.topic_page_url,
            'extended_slug': self.get_extended_slug(),
            'ancestor_topics': ancestor_topics,
            'top_level_topic': db.get(self.ancestor_keys[-2]).id if len(self.ancestor_keys) > 1 else self.id,
            'videos': videos_dict,
            'previous_topic_title': previous_topic.standalone_title if previous_topic else None,
            'previous_topic_video': previous_video.readable_id if previous_video else None,
            'previous_topic_subtopic_slug': previous_video_topic.get_extended_slug() if previous_video_topic else None,
            'next_topic_title': next_topic.standalone_title if next_topic else None,
            'next_topic_video': next_video.readable_id if next_video else None,
            'next_topic_subtopic_slug': next_video_topic.get_extended_slug() if next_video_topic else None
        }

    # get the topic by the url slug/readable_id
    @staticmethod
    def get_by_id(id, version=None):
        if version is None:
            version = TopicVersion.get_default_version()
            if version is None:
                logging.info("No default version has been set, getting latest version instead")
                version = TopicVersion.get_latest_version()

        return Topic.all().filter("id =", id).filter("version =", version).get()

    # title is not necessarily unique - this function is needed for the old playl1st api to return a best guess
    @staticmethod
    def get_by_title(title, version=None):
        if version is None:
            version = TopicVersion.get_default_version()
            if version is None:
                logging.info("No default version has been set, getting latest version instead")
                version = TopicVersion.get_latest_version()

        return Topic.all().filter("title =", title).filter("version =", version).get()

    @staticmethod
    # parent specifies version
    def get_by_title_and_parent(title, parent):
        return Topic.all().filter("title =", title).filter("parent_keys =", parent.key()).get()

    @staticmethod
    def get_root(version=None):
        if not version:
            version = TopicVersion.get_default_version()
        return Topic.all().filter('id =', 'root').filter('version =', version).get()

    @staticmethod
    def get_new_id(parent, title, version):
        potential_id = title.lower()
        potential_id = re.sub('[^a-z0-9]', '-', potential_id);
        potential_id = re.sub('-+$', '', potential_id)  # remove any trailing dashes (see issue 1140)
        potential_id = re.sub('^-+', '', potential_id)  # remove any leading dashes (see issue 1526)

        if potential_id[0].isdigit():
            potential_id = parent.id + "-" + potential_id

        number_to_add = 0
        current_id = potential_id
        while True:
            # need to make this an ancestor query to make sure that it can be used within transactions
            matching_topic = Topic.all().filter('id =', current_id).filter('version =', version).get()

            if matching_topic is None: #id is unique so use it and break out
                return current_id
            else: # id is not unique so will have to go through loop again
                number_to_add += 1
                current_id = '%s-%s' % (potential_id, number_to_add)

    @staticmethod
    def get_new_key_name():
        return base64.urlsafe_b64encode(os.urandom(30))

    @layer_cache.cache_with_key_fxn(lambda self:
        "topic_get_previous_topic_%s_v%s" % (
            self.key(), Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def get_previous_topic(self):
        if self.parent_keys:
            parent_topic = db.get(self.parent_keys[0])
            prev_index = parent_topic.child_keys.index(self.key()) - 1

            while prev_index >= 0:
                prev_topic = db.get(parent_topic.child_keys[prev_index])
                if not prev_topic.hide:
                    return prev_topic

                prev_index -= 1

            return parent_topic.get_previous_topic()

        return None

    @layer_cache.cache_with_key_fxn(lambda self:
        "topic_get_next_topic_%s_v%s" % (
            self.key(), Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def get_next_topic(self):
        if self.parent_keys:
            parent_topic = db.get(self.parent_keys[0])
            next_index = parent_topic.child_keys.index(self.key()) + 1

            while next_index < len(parent_topic.child_keys):
                next_topic = db.get(parent_topic.child_keys[next_index])
                if not next_topic.hide:
                    return next_topic

                next_index += 1

            return parent_topic.get_next_topic()

        return None

    @layer_cache.cache_with_key_fxn(lambda self:
        "topic_get_first_video_%s_v%s" % (
            self.key(), Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def get_first_video_and_topic(self):
        videos = Topic.get_cached_videos_for_topic(self)
        if videos:
            return (videos[0], self)

        for key in self.child_keys:
            if key.kind() == 'Topic':
                topic = db.get(key)
                if not topic.hide:
                    ret = topic.get_first_video_and_topic()
                    if ret != (None, None):
                        return ret

        return (None, None)

    @layer_cache.cache_with_key_fxn(lambda self:
        "topic_get_last_video_%s_v%s" % (
            self.key(), Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def get_last_video_and_topic(self):
        videos = Topic.get_cached_videos_for_topic(self)
        if videos:
            return (videos[-1], self)

        for key in reversed(self.child_keys):
            if key.kind() == 'Topic':
                topic = db.get(key)
                if not topic.hide:
                    ret = topic.get_last_video_and_topic()
                    if ret != (None, None):
                        return ret

        return (None, None)

    def update_ancestor_keys(self, topic_dict=None):
        """ Update the ancestor_keys by using the parents' ancestor_keys.

    		furthermore updates the ancestors of all the descendants
    		returns the list of entities updated (they still need to be put into the db) """

        # topic_dict keeps a dict of all descendants and all parent's of those descendants so we don't have to get them from the datastore again
        if topic_dict is None:
            descendants = Topic.all().filter("ancestor_key =", self)
            topic_dict = dict((d.key(), d) for d in descendants)
            topic_dict[self.key()] = self

            # as topics in the tree may have more than one parent we need to add their other parents to the dict
            unknown_parent_dict = {}
            for topic_key, topic in topic_dict.iteritems():
                # add each parent_key that is not already in the topic_dict to the unknown_parents that we still need to get
                unknown_parent_dict.update(dict((p, True) for p in topic.parent_keys if p not in topic_dict))

            if unknown_parent_dict:
                # get the unknown parents from the database and then update the topic_dict to include them
                unknown_parent_dict.update(dict((p.key(), p) for p in db.get(unknown_parent_dict.keys())))
                topic_dict.update(unknown_parent_dict)

        # calculate the new ancestor keys for self
        ancestor_keys = set()
        for parent_key in self.parent_keys:
            ancestor_keys.update(topic_dict[parent_key].ancestor_keys)
            ancestor_keys.add(parent_key)

        # update the ancestor_keys and keep track of the entity if we have changed it
        changed_entities = set()
        if set(self.ancestor_keys) != ancestor_keys:
            self.ancestor_keys = list(ancestor_keys)
            changed_entities.add(self)

            # recursively look at the child entries and update their ancestors, keeping track of which entities ancestors changed
            for child_key in self.child_keys:
                if child_key.kind == "Topic":
                    child = topic_dict[child_key]
                    changed_entities.update(child.update_ancestors(topic_dict))

        return changed_entities

    def move_child(self, child, new_parent, new_parent_pos):
        if new_parent.version.default:
            raise Exception("You can't edit the default version")

        # remove the child
        old_index = self.child_keys.index(child.key())
        del self.child_keys[old_index]
        updated_entities = set([self])

        # check to make sure the new parent is different than the old one
        if new_parent.key() != self.key():
            # add the child to the new parent's children list
            new_parent.child_keys.insert(int(new_parent_pos), child.key())
            updated_entities.add(new_parent)

            if isinstance(child, Topic):
                # if the child is a topic make sure to update its parent list
                old_index = child.parent_keys.index(self.key())
                del child.parent_keys[old_index]
                child.parent_keys.append(new_parent.key())
                updated_entities.add(child)
                # now that the child's parent has changed, go to the child all of the child's descendants and update their ancestors
                updated_entities.update(child.update_ancestor_keys())

        else:
            # they are moving the item within the same node, so just update self with the new position
            self.child_keys.insert(int(new_parent_pos), child.key())

        def move_txn():
            db.put(updated_entities)

        self.version.update()
        return db.run_in_transaction(move_txn)

    # Ungroup takes all of a topics children, moves them up a level, then
    # deletes the topic
    def ungroup(self):
        parent = db.get(self.parent_keys[0])
        pos = parent.child_keys.index(self.key())
        children = db.get(self.child_keys)
        for i, child in enumerate(children):
            self.move_child(child, parent, pos + i)
        parent.delete_child(self)

    def copy(self, title, parent=None, **kwargs):
        if not kwargs.has_key("version") and parent is not None:
            kwargs["version"] = parent.version

        if kwargs["version"].default:
            raise Exception("You can't edit the default version")

        if self.parent():
            kwargs["parent"] = Topic.get_root(kwargs["version"])

        if not kwargs.has_key("id"):
            kwargs["id"] = Topic.get_new_id(parent, title, kwargs["version"])

        kwargs["key_name"] = Topic.get_new_key_name()

        topic = Topic.get_by_key_name(kwargs["key_name"])
        if topic is not None:
            raise Exception("Trying to insert a topic with the duplicate key_name '%s'" % kwargs["key_name"])

        kwargs["title"] = title
        kwargs["parent_keys"] = [parent.key()] if parent else []
        kwargs["ancestor_keys"] = kwargs["parent_keys"][:]
        kwargs["ancestor_keys"].extend(parent.ancestor_keys if parent else [])

        new_topic = util.clone_entity(self, **kwargs)

        return db.run_in_transaction(Topic._insert_txn, new_topic)

    def add_child(self, child, pos=None):
        if self.version.default:
            raise Exception("You can't edit the default version")

        if child.key() in self.child_keys:
            raise Exception("The child %s already appears in %s" % (child.title, self.title))

        if pos is None:
            self.child_keys.append(child.key())
        else:
            self.child_keys.insert(int(pos), child.key())

        entities_updated = set([self])

        if isinstance(child, Topic):
            child.parent_keys.append(self.key())
            entities_updated.add(child)
            entities_updated.update(child.update_ancestor_keys())

        def add_txn():
            db.put(entities_updated)

        self.version.update()
        return db.run_in_transaction(add_txn)

    def delete_child(self, child):
        if self.version.default:
            raise Exception("You can't edit the default version")

        # remove the child key from self
        self.child_keys = [c for c in self.child_keys if c != child.key()]

        # remove self from the child's parents
        if isinstance(child, Topic):
            child.parent_keys = [p for p in child.parent_keys if p != self.key()]
            num_parents = len(child.parent_keys)
            descendants = Topic.all().filter("ancestor_keys =", child.key()).fetch(10000)

            # if there are still other parents
            if num_parents:
                changed_descendants = child.update_ancestor_keys()
            else:
                #TODO: If the descendants still have other parents we shouldn't be deleting them - if we are sure we want multiple parents will need to implement this
                descendants.append(child)

        def delete_txn():
            self.put()
            if isinstance(child, Topic):
                if num_parents:
                    db.put(changed_descendants)
                else:
                    db.delete(descendants)

        self.version.update()
        db.run_in_transaction(delete_txn)

    def delete_tree(self):
        parents = db.get(self.parent_keys)
        for parent in parents:
            parent.delete_child(self)

    @staticmethod
    def _insert_txn(new_topic):
        new_topic.put()
        parents = db.get(new_topic.parent_keys)
        for parent in parents:
            parent.child_keys.append(new_topic.key())
            parent.put()

        if new_topic.child_keys:
            child_topic_keys = [c for c in new_topic.child_keys if c.kind() == "Topic"]
            child_topics = db.get(child_topic_keys)
            for child in child_topics:
                child.parent_keys.append(topic.key())
                child.ancestor_keys.append(topic.key())

            all_descendant_keys = {} # used to make sure we don't loop
            descendant_keys = {}
            descendants = child_topics
            while True: # should iterate n+1 times making n db.gets() where n is the tree depth under topic
                for descendant in descendants:
                    descendant_keys.update(dict((key, True) for key in descendant.child_keys if key.kind() == "Topic" and not all_descendant_keys.has_key(key)))
                if not descendant_keys: # no more topic descendants that we haven't already seen before
                    break

                all_descendant_keys.update(descendant_keys)
                descendants = db.get(descendant_keys.keys())
                for descendant in descendants:
                    descendant.ancestor_keys = topic.key()
                descendant_keys = {}

        return new_topic


    @staticmethod
    def insert(title, parent=None, **kwargs):
        if kwargs.has_key("version"):
            version = kwargs["version"]
            del kwargs["version"]
        else:
            if parent is not None:
                version = parent.version
            else:
                version = TopicVersion.get_edit_version()

        if version.default:
            raise Exception("You can't edit the default version")

        if kwargs.has_key("id") and kwargs["id"]:
            id = kwargs["id"]
            del kwargs["id"]
        else:
            id = Topic.get_new_id(parent, title, version)
            logging.info("created a new id %s for %s" % (id, title))

        if not kwargs.has_key("standalone_title"):
            kwargs["standalone_title"] = title

        key_name = Topic.get_new_key_name()

        topic = Topic.get_by_key_name(key_name)
        if topic is not None:
            raise Exception("Trying to insert a topic with the duplicate key_name '%s'" % key_name)

        if parent:
            root = Topic.get_root(version)
            parent_keys = [parent.key()]
            ancestor_keys = parent_keys[:]
            ancestor_keys.extend(parent.ancestor_keys)

            new_topic = Topic(parent=root, # setting the root to be the parent so that inserts and deletes can be done in a transaction
                              key_name=key_name,
                              version=version,
                              id=id,
                              title=title,
                              parent_keys=parent_keys,
                              ancestor_keys=ancestor_keys)

        else:
            root = Topic.get_root(version)

            new_topic = Topic(parent=root,
                              key_name=key_name,
                              version=version,
                              id=id,
                              title=title)

        for key in kwargs:
            setattr(new_topic, key, kwargs[key])

        version.update()
        return db.run_in_transaction(Topic._insert_txn, new_topic)

    def update(self, **kwargs):
        if self.version.default:
            raise Exception("You can't edit the default version")


        if "put" in kwargs:
            put = kwargs["put"]
            del kwargs["put"]
        else:
            put = True

        changed = False
        if "id" in kwargs and kwargs["id"] != self.id:

            existing_topic = Topic.get_by_id(kwargs["id"], self.version)
            if not existing_topic:
                self.id = kwargs["id"]
                changed = True
            else:
                pass # don't allow people to change the slug to a different nodes slug
            del kwargs["id"]

        for attr, value in kwargs.iteritems():
            if getattr(self, attr) != value:
                setattr(self, attr, value)
                changed = True

        if changed:
            if put:
                self.put()
                self.version.update()
            return self

    @layer_cache.cache_with_key_fxn(
    lambda self, types=[], include_hidden=False:
            "topic.make_tree_%s_%s_%s" % (
            self.key(), types, include_hidden),
            layer=layer_cache.Layers.Memcache)
    def make_tree(self, types=[], include_hidden=False):
        if include_hidden:
            nodes = Topic.all().filter("ancestor_keys =", self.key()).run()
        else:
            nodes = Topic.all().filter("ancestor_keys =", self.key()).filter("hide = ", False).run()

        node_dict = dict((node.key(), node) for node in nodes)
        node_dict[self.key()] = self # in case the current node is hidden (like root is)

        contentKeys = []
        # cycle through the nodes adding its children to the contentKeys that need to be gotten
        for key, descendant in node_dict.iteritems():
            contentKeys.extend([c for c in descendant.child_keys if not node_dict.has_key(c) and (c.kind() in types or (len(types) == 0 and c.kind() != "Topic"))])

        # get all content that belongs in this tree
        contentItems = db.get(contentKeys)
        content_dict = dict((content.key(), content) for content in contentItems)

        if "Exercise" in types or len(types) == 0:
            evs = ExerciseVideo.all().fetch(10000)
            exercise_dict = dict((k, v) for k, v in content_dict.iteritems() if
                          (k.kind() == "Exercise"))
            video_dict = dict((k, v) for k, v in content_dict.iteritems() if
                          (k.kind() == "Video"))

            Exercise.add_related_videos_prop(exercise_dict, evs, video_dict)

        # make any content changes for this version
        changes = VersionContentChange.get_updated_content_dict(self.version)
        type_changes = dict((k, c) for k, c in changes.iteritems() if
                       (k.kind() in types or len(types) == 0))
        content_dict.update(type_changes)

        node_dict.update(content_dict)

        # cycle through the nodes adding each to its parent's children list
        for key, descendant in node_dict.iteritems():
            if hasattr(descendant, "child_keys"):
                descendant.children = [node_dict[c] for c in descendant.child_keys if node_dict.has_key(c)]

        # return the entity that was passed in, now with its children, and its descendants children all added
        return node_dict[self.key()]

    def search_tree_traversal(self, query, node_dict, path, matching_paths, matching_nodes):
        match = False

        if self.title.lower().find(query) > -1:
            match_path = path[:]
            match_path.append('Topic')
            matching_paths.append(match_path)
            match = True

        for child_key in self.child_keys:
            if node_dict.has_key(child_key):
                child = node_dict[child_key]

                if child_key.kind() == 'Topic':
                    sub_path = path[:]
                    sub_path.append(child.id)
                    if child.search_tree_traversal(query, node_dict, sub_path, matching_paths, matching_nodes):
                        match = True

                else:
                    title = getattr(child, "title", getattr(child, "display_name", ""))
                    id = getattr(child, "id", getattr(child, "readable_id", getattr(child, "name", child.key().id())))
                    if title.lower().find(query) > -1 or str(id).lower().find(query) > -1:
                        match_path = path[:]
                        match_path.append(id)
                        match_path.append(child_key.kind())
                        matching_paths.append(match_path)
                        match = True
                        matching_nodes.append(child)

        if match:
            matching_nodes.append(self.get_visible_data(node_dict))

        return match

    def search_tree(self, query):
        query = query.strip().lower()

        nodes = Topic.all().filter("ancestor_keys =", self.key()).run()

        node_dict = dict((node.key(), node) for node in nodes)
        node_dict[self.key()] = self # in case the current node is hidden (like root is)

        contentKeys = []
        # cycle through the nodes adding its children to the contentKeys that need to be gotten
        for key, descendant in node_dict.iteritems():
            contentKeys.extend([c for c in descendant.child_keys if not node_dict.has_key(c) and c.kind() != "Topic"])

        # get all content that belongs in this tree
        contentItems = db.get(contentKeys)
        # add the content to the node dict
        for content in contentItems:
            node_dict[content.key()] = content

        matching_paths = []
        matching_nodes = []

        self.search_tree_traversal(query, node_dict, [], matching_paths, matching_nodes)

        return {
            "paths": matching_paths,
            "nodes": matching_nodes
        }

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda version=None, include_hidden=False:
        "topic.get_all_topic_%s_%s" % (
            (str(version.number) + str(version.updated_on)) if version
            else Setting.topic_tree_version(),
            include_hidden),
        layer=layer_cache.Layers.Memcache)
    def get_all_topics(version=None, include_hidden=False):
        if not version:
            version = TopicVersion.get_default_version()

        query = Topic.all().filter("version =", version)
        if not include_hidden:
            query.filter("hide =", False)

        return query.fetch(10000)

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda version=None:
        "topic.get_visible_topics_%s" % (
            version.key() if version else Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def get_visible_topics(version=None):
        topics = Topic.get_all_topics(version, False)
        return [t for t in topics]


    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda version=None, include_hidden=False:
        "topic.get_super_topics_%s_%s" % (
            (str(version.number) + str(version.updated_on))  if version
            else Setting.topic_tree_version(),
            include_hidden),
        layer=layer_cache.Layers.Memcache)
    def get_super_topics(version=None):
        topics = Topic.get_visible_topics()
        return [t for t in topics if t.id in Topic._super_topic_ids]

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda version=None, include_hidden=False:
        "topic.get_rolled_up_top_level_topics_%s_%s" % (
            (str(version.number) + str(version.updated_on))  if version
            else Setting.topic_tree_version(),
            include_hidden),
        layer=layer_cache.Layers.Memcache)
    def get_rolled_up_top_level_topics(version=None, include_hidden=False):
        topics = Topic.get_all_topics(version, include_hidden)

        super_topics = Topic.get_super_topics()
        super_topic_keys = [t.key() for t in super_topics]

        rolled_up_topics = super_topics[:]
        for topic in topics:
            # if the topic is a subtopic of a super topic
            if set(super_topic_keys) & set(topic.ancestor_keys):
                continue

            for child_key in topic.child_keys:
                 if child_key.kind() != "Topic":
                    rolled_up_topics.append(topic)
                    break

        return rolled_up_topics

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda types=None, version=None, include_hidden=False:
        "topic.get_filled_rolled_up_top_level_topics_%s_%s" % (
            (str(version.number) + str(version.updated_on))  if version
            else Setting.topic_tree_version(),
            include_hidden),
        layer=layer_cache.Layers.Memcache)
    def get_filled_rolled_up_top_level_topics(types=None, version=None, include_hidden=False):
        if types is None:
            types = []

        topics = Topic.get_all_topics(version, include_hidden)
        topic_dict = dict((t.key(), t) for t in topics)

        super_topics = Topic.get_super_topics()

        def rolled_up_child_content_keys(topic):
            child_keys = []
            for key in topic.child_keys:
                if key.kind() == "Topic":
                    child_keys += rolled_up_child_content_keys(topic_dict[key])
                elif (len(types) == 0) or key.kind() in types:
                    child_keys.append(key)

            return child_keys

        for topic in super_topics:
            topic.child_keys = rolled_up_child_content_keys(topic)

        super_topic_keys = [t.key() for t in super_topics]

        rolled_up_topics = super_topics[:]
        for topic in topics:
            # if the topic is a subtopic of a super topic
            if set(super_topic_keys) & set(topic.ancestor_keys):
                continue

            for child_key in topic.child_keys:
                 if child_key.kind() != "Topic":
                    rolled_up_topics.append(topic)
                    break


        child_dict = {}
        for topic in rolled_up_topics:
            child_dict.update(dict((key, True) for key in topic.child_keys
                                   if key.kind() in types or
                                   (len(types) == 0 and key.kind() != "Topic")))

        child_dict.update(dict((e.key(), e) for e in db.get(child_dict.keys())))

        for topic in rolled_up_topics:
            topic.children = [child_dict[key] for key in topic.child_keys if child_dict.has_key(key)]

        return rolled_up_topics


    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda version=None, include_hidden=False:
        "topic.get_content_topics_%s_%s" % (
            (str(version.number) + str(version.updated_on))  if version
            else Setting.topic_tree_version(),
            include_hidden),
        layer=layer_cache.Layers.Memcache)
    def get_content_topics(version=None, include_hidden=False):
        topics = Topic.get_all_topics(version, include_hidden)

        content_topics = []
        for topic in topics:
            for child_key in topic.child_keys:
                if child_key.kind() != "Topic":
                    content_topics.append(topic)
                    break

        content_topics.sort(key=lambda topic: topic.standalone_title)
        return content_topics

    @staticmethod
    def get_filled_content_topics(types=None, version=None, include_hidden=False):
        if types is None:
            types = []

        topics = Topic.get_content_topics(version)

        child_dict = {}
        for topic in topics:
            child_dict.update(dict((key, True) for key in topic.child_keys if key.kind() in types or (len(types) == 0 and key.kind() != "Topic")))
        child_dict.update(dict((e.key(), e) for e in db.get(child_dict.keys())))

        for topic in topics:
            topic.children = [child_dict[key] for key in topic.child_keys if child_dict.has_key(key)]

        return topics

    @staticmethod
    def get_exercise_topics(version=None):
        """ Get all topics containing live exercises as direct children.
        This does *not* currently return topics with exercise-containing subtopics.
        """
        # TODO: when we want this to support multiple layers of topics, we'll
        # need a different interaction w/ Topic.
        topics = Topic.get_filled_content_topics(types=["Exercise"], version=version)

        # Topics in ignored_topics will not show up on the knowledge map,
        # have topic exercise badges created for them, etc.
        ignored_topics = [
            "New and Noteworthy",
        ]

        # Filter out New and Noteworthy special-case topic. It might have exercises,
        # but we don't want it to own a badge.
        topics = [t for t in topics if t.title not in ignored_topics]

        # Remove non-live exercises
        for topic in topics:
            topic.children = [exercise for exercise in topic.children if exercise.live]

        # Filter down to only topics that have live exercises
        return [topic for topic in topics if len(topic.children) > 0]

    @staticmethod
    def _get_children_of_kind(topic, kind, include_descendants=False, include_hidden=False):
        keys = [child_key for child_key in topic.child_keys if not kind or child_key.kind() == kind]
        if include_descendants:

            subtopics = Topic.all().filter("ancestor_keys =", topic.key())
            if not include_hidden:
                subtopics.filter("hide =", False)
            subtopics.run()

            for subtopic in subtopics:
                keys.extend([key for key in subtopic.child_keys if not kind or key.kind() == kind])

        nodes = db.get(keys)
        if not kind:
            nodes.extend(subtopics)

        return nodes

    def get_urls(self, include_descendants=False, include_hidden=False):
        return Topic._get_children_of_kind(self, "Url", include_descendants,
                                           include_hidden)

    def get_exercises(self, include_descendants=False, include_hidden=False):
        exercises = Topic._get_children_of_kind(self, "Exercise",
                                           include_descendants, include_hidden)

        # Topic.get_exercises should only return live exercises for now, as
        # its results are cached and should never show users unpublished exercises.
        return [ex for ex in exercises if ex.live]

    def get_videos(self, include_descendants=False, include_hidden=False):
        return Topic._get_children_of_kind(self, "Video", include_descendants,
                                           include_hidden)

    def get_child_topics(self, include_descendants=False, include_hidden=False):
        return Topic._get_children_of_kind(self, "Topic", include_descendants,
                                           include_hidden)

    def get_descendants(self, include_hidden=False):
        subtopics = Topic.all().filter("ancestor_keys =", self.key())
        if not include_hidden:
            subtopics.filter("hide =", False)
        return subtopics.fetch(10000)

    def delete_descendants(self):
        query = Topic.all(keys_only=True)
        descendants = query.filter("ancestor_keys =", self.key()).fetch(10000)
        db.delete(descendants)

    def get_exercise_badge(self):
        """ Returns the TopicExerciseBadge associated with this topic
        """
        badge_name = topic_exercise_badges.TopicExerciseBadge.name_for_topic_key_name(self.key().name())
        return util_badges.all_badges_dict().get(badge_name, None)

    @staticmethod
    @layer_cache.cache_with_key_fxn(lambda
        topic, include_descendants=False, version=None:
        "%s_videos_for_topic_%s_v%s" % (
            "descendant" if include_descendants else "child",
            topic.key(),
            version.key() if version else Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache)
    def get_cached_videos_for_topic(topic, include_descendants=False, version=None):
        return Topic._get_children_of_kind(topic, "Video", include_descendants)

    @staticmethod
    def reindex(version):
        import search
        items = search.StemmedIndex.all().filter("parent_kind", "Topic").run()
        db.delete(items)

        topics = Topic.get_content_topics(version)
        for topic in topics:
            logging.info("Indexing topic " + topic.title + " (" + str(topic.key()) + ")")
            topic.index()
            topic.indexed_title_changed()

    def get_user_progress(self, user_data, flatten=True):

        def get_user_video_progress(video_id, user_video_dict):
            status_flags = {}

            id = '.v%d' % video_id

            if id in user_video_dict['completed']:
                status_flags["VideoCompleted"] = 1
                status_flags["VideoStarted"] = 1

            if id in user_video_dict['started']:
                status_flags["VideoStarted"] = 1

            if status_flags != {}:
                return {
                    "kind": "Video",
                    "id": video_id,
                    "status_flags": status_flags
                }

            return None

        def get_user_exercise_progress(exercise_id, user_exercise_dict):
            status_flags = {}

            if exercise_id in user_exercise_dict:
                exercise_dict = user_exercise_dict[exercise_id]

                if exercise_dict["proficient"]:
                    status_flags["ExerciseProficient"] = 1

                if exercise_dict["struggling"]:
                    status_flags["ExerciseStruggling"] = 1

                if exercise_dict["total_done"] > 0:
                    status_flags["ExerciseStarted"] = 1

            if status_flags != {}:
                return {
                    "kind": "Exercise",
                    "id": exercise_id,
                    "status_flags": status_flags
                }

            return None

        def get_user_progress_recurse(flat_output, topic, topics_dict, user_video_dict, user_exercise_dict):

            children = []
            status_flags = {}
            aggregates = {
                "video": {},
                "exercise": {},
                "topic": {}
            }
            counts = {
                "video": 0,
                "exercise": 0,
                "topic": 0
            }

            for child_key in topic.child_keys:
                if child_key.kind() == "Topic":
                    if child_key in topics_dict:
                        child_topic = topics_dict[child_key]
                        progress = get_user_progress_recurse(flat_output, child_topic, topics_dict, user_video_dict, user_exercise_dict)
                        if progress:
                            children.append(progress)
                            if flat_output:
                                flat_output["topic"][child_topic.id] = progress
                        counts["topic"] += 1

                elif child_key.kind() == "Video":
                    video_id = child_key.id()
                    progress = get_user_video_progress(video_id, user_video_dict)
                    if progress:
                        children.append(progress)
                        if flat_output:
                            flat_output["video"][video_id] = progress
                    counts["video"] += 1

                elif child_key.kind() == "Exercise":
                    exercise_id = child_key.id()
                    progress = get_user_exercise_progress(exercise_id, user_exercise_dict)
                    if progress:
                        children.append(progress)
                        if flat_output:
                            flat_output["exercise"][exercise_id] = progress
                    counts["exercise"] += 1
                    pass

            for child_stat in children:
                kind = child_stat["kind"].lower()
                for flag, value in child_stat["status_flags"].iteritems():
                    if flag not in aggregates[kind]:
                        aggregates[kind][flag] = 0
                    aggregates[kind][flag] += value

            for kind, aggregate in aggregates.iteritems():
                for flag, value in aggregate.iteritems():
                    if value >= counts[kind]:
                        status_flags[flag] = 1

            if children != [] or status_flags != {}:
                stats = {
                    "kind": "Topic",
                    "id": topic.id,
                    "status_flags": status_flags,
                    "aggregates": aggregates,
                    "counts": counts
                }
                if not flat_output:
                    stats["children"] = children
                return stats
            else:
                return None

        user_video_css = UserVideoCss.get_for_user_data(user_data)
        if user_video_css:
            user_video_dict = pickle.loads(user_video_css.pickled_dict)
        else:
            user_video_dict = {}

        user_exercise_graph = UserExerciseGraph.get(user_data)
        user_exercise_dict = dict((exdict["id"], exdict) for name, exdict in user_exercise_graph.graph.iteritems())

        topics = Topic.get_visible_topics()
        topics_dict = dict((topic.key(), topic) for topic in topics)

        flat_output = None
        if flatten:
            flat_output = {
                "topic": {},
                "video": {},
                "exercise": {}
            }

        progress_tree = get_user_progress_recurse(flat_output, self, topics_dict, user_video_dict, user_exercise_dict)

        if flat_output:
            flat_output["topic"][self.id] = progress_tree
            return flat_output
        else:
            return progress_tree

def topictree_import_task(version_id, topic_id, publish, tree_json_compressed):
    from api.v1 import exercise_save_data
    import zlib

    try:
        tree_json = pickle.loads(zlib.decompress(tree_json_compressed))

        logging.info("starting import")
        version = TopicVersion.get_by_id(version_id)
        parent = Topic.get_by_id(topic_id, version)

        topics = Topic.get_all_topics(version, True)
        logging.info("got all topics")
        topic_dict = dict((topic.id, topic) for topic in topics)
        topic_keys_dict = dict((topic.key(), topic) for topic in topics)

        videos = Video.get_all()
        logging.info("got all videos")
        video_dict = dict((video.readable_id, video) for video in videos)

        exercises = Exercise.get_all_use_cache()
        logging.info("got all exercises")
        exercise_dict = dict((exercise.name, exercise) for exercise in exercises)

        urls = Url.all()
        url_dict = dict((url.id, url) for url in urls)
        logging.info("got all urls")

        all_entities_dict = {}
        new_content_keys = []

        # on dev server dont record new items in ContentVersionChanges
        if App.is_dev_server:
            put_change = False
        else:
            put_change = True

        # delete all subtopics of node we are copying over the same topic
        if tree_json["id"] == parent.id:
            parent.delete_descendants()

        # adds key to each entity in json tree, if the node is not in the tree then add it
        def add_keys_json_tree(tree, parent, do_exercises, i=0, prefix=None):
            pos = ((prefix + ".") if prefix else "") + str(i)

            if not do_exercises and tree["kind"] == "Topic":
                if tree["id"] in topic_dict:
                    topic = topic_dict[tree["id"]]
                    tree["key"] = topic.key()
                else:
                    kwargs = dict((str(key), value) for key, value in tree.iteritems() if key in ['standalone_title', 'description', 'tags'])
                    kwargs["version"] = version
                    topic = Topic.insert(title=tree['title'], parent=parent, **kwargs)
                    logging.info("%s: added topic %s" % (pos, topic.title))
                    tree["key"] = topic.key()
                    topic_dict[tree["id"]] = topic

                # if this topic is not the parent topic (ie. its not root, nor the
                # topic_id you are updating)
                if (parent.key() != topic.key() and
                    # and this topic is not in the new parent
                    topic.key() not in parent.child_keys and
                    # if it already exists in a topic
                    len(topic.parent_keys) and
                    # and that topic is not the parent topic
                    topic.parent_keys[0] != parent.key()):

                    # move it from that old parent topic, its position in the new
                    # parent does not matter as child_keys will get written over
                    # later.  move_child is needed only to make sure that the
                    # parent_keys and ancestor_keys will all match up correctly
                    old_parent = topic_keys_dict[topic.parent_keys[0]]
                    logging.info("moving topic %s from %s to %s" % (topic.id,
                        old_parent.id, parent.id))
                    old_parent.move_child(topic, parent, 0)

                all_entities_dict[tree["key"]] = topic

            elif not do_exercises and tree["kind"] == "Video":
                if tree["readable_id"] in video_dict:
                    video = video_dict[tree["readable_id"]]
                    tree["key"] = video.key()
                else:
                    changeable_props = ["youtube_id", "url", "title", "description",
                                        "keywords", "duration", "readable_id",
                                        "views"]
                    video = VersionContentChange.add_new_content(Video,
                                                                    version,
                                                                    tree,
                                                                    changeable_props,
                                                                    put_change)
                    logging.info("%s: added video %s" % (pos, video.title))
                    new_content_keys.append(video.key())
                    tree["key"] = video.key()
                    video_dict[tree["readable_id"]] = video

                all_entities_dict[tree["key"]] = video

            elif do_exercises and tree["kind"] == "Exercise":
                if tree["name"] in exercise_dict:
                    tree["key"] = exercise_dict[tree["name"]].key() if tree["name"] in exercise_dict else None
                else:
                    if "related_videos" in tree:
                        # adding keys to entity tree so we don't need to look it up
                        # again when creating the video in add_new_content
                        tree["related_video_keys"] = []
                        for readable_id in tree["related_videos"]:
                            video = video_dict[readable_id]
                            tree["related_video_keys"].append(video.key())
                    exercise = exercise_save_data(version, tree, None, put_change)
                    logging.info("%s: added Exercise %s" % (pos, exercise.name))
                    new_content_keys.append(exercise.key())
                    tree["key"] = exercise.key()
                    exercise_dict[tree["name"]] = exercise

                all_entities_dict[tree["key"]] = exercise_dict[tree["name"]]

            elif not do_exercises and tree["kind"] == "Url":
                if tree["id"] in url_dict:
                    url = url_dict[tree["id"]]
                    tree["key"] = url.key()
                else:
                    changeable_props = ["tags", "title", "url"]
                    url = VersionContentChange.add_new_content(Url,
                                                               version,
                                                               tree,
                                                               changeable_props,
                                                               put_change)
                    logging.info("%s: added Url %s" % (pos, url.title))
                    new_content_keys.append(url.key())
                    tree["key"] = url.key()
                    url_dict[tree["id"]] = url

                all_entities_dict[tree["key"]] = url

            i = 0
            # recurse through the tree's children
            if "children" in tree:
                for child in tree["children"]:
                    add_keys_json_tree(child, topic_dict[tree["id"]], do_exercises, i, pos)
                    i += 1

        add_keys_json_tree(tree_json, parent, do_exercises=False)

        # add related_videos prop to exercises
        evs = ExerciseVideo.all().fetch(10000)
        exercise_key_dict = dict((e.key(), e) for e in exercises)
        video_key_dict = dict((v.key(), v) for v in video_dict.values())
        Exercise.add_related_videos_prop(exercise_key_dict, evs, video_key_dict)

        # exercises need to be done after, because if they reference ExerciseVideos
        # those Videos have to already exist
        add_keys_json_tree(tree_json, parent, do_exercises=True)

        logging.info("added keys to nodes")

        def add_child_keys_json_tree(tree):
            if tree["kind"] == "Topic":
                tree["child_keys"] = []
                if "children" in tree:
                    for child in tree["children"]:
                        tree["child_keys"].append(child["key"])
                        add_child_keys_json_tree(child)

        add_child_keys_json_tree(tree_json)
        logging.info("added children keys")

        def extract_nodes(tree, nodes):
            if "children" in tree:
                for child in tree["children"]:
                    nodes.update(extract_nodes(child, nodes))
                del(tree["children"])
            nodes[tree["key"]] = tree
            return nodes

        nodes = extract_nodes(tree_json, {})
        logging.info("extracted %i nodes" % len(nodes))
        changed_nodes = []

        i = 0
        # now loop through all the nodes
        for key, node in nodes.iteritems():
            if node["kind"] == "Topic":
                topic = all_entities_dict[node["key"]]
                logging.info("%i/%i Updating any change to Topic %s" % (i, len(nodes), topic.title))

                kwargs = (dict((str(key), value) for key, value in node.iteritems()
                        if key in ['id', 'title', 'standalone_title', 'description',
                        'tags', 'hide', 'child_keys']))
                kwargs["version"] = version
                kwargs["put"] = False
                if topic.update(**kwargs):
                    changed_nodes.append(topic)

            elif node["kind"] == "Video" and node["key"] not in new_content_keys:
                video = all_entities_dict[node["key"]]
                logging.info("%i/%i Updating any change to Video %s" % (i, len(nodes), video.title))

                change = VersionContentChange.add_content_change(video,
                    version,
                    node,
                    ["readable_id", "title", "youtube_id", "description", "keywords"])
                if change:
                    logging.info("changed")

            elif node["kind"] == "Exercise" and node["key"] not in new_content_keys:
                exercise = all_entities_dict[node["key"]]
                logging.info("%i/%i Updating any changes to Exercise %s" % (i, len(nodes), exercise.name))

                change = exercise_save_data(version, node, exercise)
                if change:
                    logging.info("changed")

            elif node["kind"] == "Url" and node["key"] not in new_content_keys:
                url = all_entities_dict[node["key"]]
                logging.info("%i/%i Updating any changes to Url %s" % (i, len(nodes), url.title))

                changeable_props = ["tags", "title", "url"]

                change = VersionContentChange.add_content_change(
                    url,
                    version,
                    node,
                    changeable_props)

                if change:
                    logging.info("changed")


            i += 1

        logging.info("about to put %i topic nodes" % len(changed_nodes))
        Setting.cached_content_add_date(datetime.datetime.now())
        db.put(changed_nodes)
        logging.info("done with import")

        if publish:
            version.set_default_version()

    except Exception, e:
        import traceback, StringIO
        fp = StringIO.StringIO()
        traceback.print_exc(file=fp)
        logging.error(fp.getvalue())
        logging.error("Topic import failed with %s", e)
        raise deferred.PermanentTaskFailure

    return True


class Url(db.Model):
    url = db.StringProperty()
    title = db.StringProperty(indexed=False)
    tags = db.StringListProperty()
    created_on = db.DateTimeProperty(auto_now_add=True)
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)

    # List of parent topics
    topic_string_keys = object_property.TsvProperty(indexed=False)

    @property
    def id(self):
        return self.key().id()

    # returns the first non-hidden topic
    def first_topic(self):
        if self.topic_string_keys:
            return db.get(self.topic_string_keys[0])
        return None

    @staticmethod
    @layer_cache.cache_with_key_fxn(lambda :
        "Url.get_all_%s" %
        Setting.cached_content_add_date(),
        layer=layer_cache.Layers.Memcache)
    def get_all():
        return Url.all().fetch(100000)

    @staticmethod
    def get_all_live(version=None):
        if not version:
            version = TopicVersion.get_default_version()

        root = Topic.get_root(version)
        urls = root.get_urls(include_descendants=True, include_hidden=False)

        # return only unique urls
        url_dict = dict((u.key(), u) for u in urls)
        return url_dict.values()

    @staticmethod
    def get_by_id_for_version(id, version=None):
        url = Url.get_by_id(id)
        # if there is a version check to see if there are any updates to the video
        if version:
            change = VersionContentChange.get_change_for_content(url, version)
            if change:
                url = change.updated_content(url)
        return url


class Video(Searchable, db.Model):
    youtube_id = db.StringProperty()
    url = db.StringProperty()
    title = db.StringProperty()
    description = db.TextProperty()
    keywords = db.StringProperty()
    duration = db.IntegerProperty(default=0)

    # A dict of properties that may only exist on some videos such as
    # original_url for smarthistory_videos.
    extra_properties = object_property.UnvalidatedObjectProperty()

    # Human readable, unique id that can be used in URLS.
    readable_id = db.StringProperty()

    # List of parent topics
    topic_string_keys = object_property.TsvProperty(indexed=False)

    # YouTube view count from last sync.
    views = db.IntegerProperty(default=0)

    # Date first added via KA library sync with YouTube.
    # This property hasn't always existsed, so for many old videos
    # this date may be much later than the actual YouTube upload date.
    date_added = db.DateTimeProperty(auto_now_add=True)

    # List of currently available downloadable formats for this video
    downloadable_formats = object_property.TsvProperty(indexed=False)

    _serialize_blacklist = ["downloadable_formats", "topic_string_keys"]

    INDEX_ONLY = ['title', 'keywords', 'description']
    INDEX_TITLE_FROM_PROP = 'title'
    INDEX_USES_MULTI_ENTITIES = False

    @staticmethod
    def get_relative_url(readable_id):
        return '/video/%s' % readable_id

    @property
    def relative_url(self):
        return Video.get_relative_url(self.readable_id)

    @property
    def ka_url(self):
        return util.absolute_url(self.relative_url)

    @property
    def download_urls(self):

        if self.downloadable_formats:

            # We now serve our downloads from s3. Our old archive URL template is...
            #   "http://www.archive.org/download/KA-converted-%s/%s.%s"
            # ...which we may want to fall back on in the future should s3 prices climb.

            url_template = "http://s3.amazonaws.com/KA-youtube-converted/%s.%s/%s.%s"
            url_dict = {}

            for suffix in self.downloadable_formats:
                folder_suffix = suffix

                if suffix == "png":
                    # Special case: our pngs are generated during mp4 creation
                    # and they are in the mp4 subfolders
                    folder_suffix = "mp4"

                url_dict[suffix] = url_template % (self.youtube_id, folder_suffix, self.youtube_id, suffix)

            return url_dict

        return None

    def download_video_url(self):
        download_urls = self.download_urls
        if download_urls:
            return download_urls.get("mp4")
        return None

    @staticmethod
    def youtube_thumbnail_urls(youtube_id):

        # You might think that hq > sd, but you'd be wrong -- hqdefault is 480x360;
        # sddefault is 640x480. Unfortunately, not all videos have the big one.
        hq_youtube_url = "http://img.youtube.com/vi/%s/hqdefault.jpg" % youtube_id
        sd_youtube_url = "http://img.youtube.com/vi/%s/sddefault.jpg" % youtube_id

        return {
                "hq": hq_youtube_url,
                "sd": ImageCache.url_for(sd_youtube_url, fallback_url=hq_youtube_url),
        }

    @staticmethod
    def get_for_readable_id(readable_id, version=None):
        video = None
        query = Video.all()
        query.filter('readable_id =', readable_id)
        # The following should just be:
        # video = query.get()
        # but the database currently contains multiple Video objects for a particular
        # video.  Some are old.  Some are due to a YouTube sync where the youtube urls
        # changed and our code was producing youtube_ids that ended with '_player'.
        # This hack gets the most recent valid Video object.
        key_id = 0
        for v in query:
            if v.key().id() > key_id and not v.youtube_id.endswith('_player'):
                video = v
                key_id = v.key().id()
        # End of hack

        # if there is a version check to see if there are any updates to the video
        if version:
            if video:
                change = VersionContentChange.get_change_for_content(video, version)
                if change:
                    video = change.updated_content(video)

            # if we didnt find any video, check to see if another video's readable_id has been updated to the one we are looking for
            else:
                changes = VersionContentChange.get_updated_content_dict(version)
                for key, content in changes.iteritems():
                    if (type(content) == Video and
                        content.readable_id == readable_id):
                        video = content
                        break

        return video

    @staticmethod
    @layer_cache.cache_with_key_fxn(
        lambda : "Video.get_all_%s" % (Setting.cached_content_add_date()),
        layer=layer_cache.Layers.Memcache)
    def get_all():
        return Video.all().fetch(100000)

    @staticmethod
    def get_all_live(version=None):
        if not version:
            version = TopicVersion.get_default_version()

        root = Topic.get_root(version)
        videos = root.get_videos(include_descendants=True, include_hidden=False)

        # return only unique videos
        video_dict = dict((v.key(), v) for v in videos)
        return video_dict.values()

    def has_topic(self):
        return bool(self.topic_string_keys)

    # returns the first non-hidden topic
    def first_topic(self):
        if self.topic_string_keys:
            return db.get(self.topic_string_keys[0])
        return None

    def current_user_points(self):
        user_video = UserVideo.get_for_video_and_user_data(self, UserData.current())
        if user_video:
            return points.VideoPointCalculator(user_video)
        else:
            return 0

    @staticmethod
    def get_dict(query, fxn_key):
        video_dict = {}
        for video in query.fetch(10000):
            video_dict[fxn_key(video)] = video
        return video_dict

    @layer_cache.cache_with_key_fxn(
        lambda self: "related_exercises_%s" % self.key(),
        layer=layer_cache.Layers.Memcache,
        expiration=3600 * 2)
    def related_exercises(self):
        exvids = ExerciseVideo.all()
        exvids.filter('video =', self.key())
        exercises = [ev.exercise for ev in exvids]
        exercises.sort(key=lambda e: e.h_position)
        exercises.sort(key=lambda e: e.v_position)
        return exercises

    @staticmethod
    @layer_cache.cache(expiration=3600)
    def approx_count():
        return int(Setting.count_videos()) / 100 * 100

    # Gets the data we need for the video player
    @staticmethod
    def get_play_data(readable_id, topic, discussion_options):
        video = None

        # If we got here, we have a readable_id and a topic, so we can display
        # the topic and the video in it that has the readable_id.  Note that we don't
        # query the Video entities for one with the requested readable_id because in some
        # cases there are multiple Video objects in the datastore with the same readable_id
        # (e.g. there are 2 "Order of Operations" videos).
        videos = Topic.get_cached_videos_for_topic(topic)
        previous_video = None
        next_video = None
        for v in videos:
            if v.readable_id == readable_id:
                v.selected = 'selected'
                video = v
            elif video is None:
                previous_video = v
            else:
                next_video = v
                break

        if video is None:
            return None

        previous_video_dict = {
            "readable_id": previous_video.readable_id,
            "key_id": previous_video.key().id(),
            "title": previous_video.title
        } if previous_video else None

        next_video_dict = {
            "readable_id": next_video.readable_id,
            "key_id": next_video.key().id(),
            "title": next_video.title
        } if next_video else None

        if App.offline_mode:
            video_path = "/videos/" + get_mangled_topic_name(topic.id) + "/" + video.readable_id + ".flv"
        else:
            video_path = video.download_video_url()

        if video.description == video.title:
            video.description = None

        related_exercises = video.related_exercises()
        button_top_exercise = None
        if related_exercises:
            def ex_to_dict(exercise):
                return {
                    'name': exercise.display_name,
                    'url': exercise.relative_url,
                }
            button_top_exercise = ex_to_dict(related_exercises[0])

        user_video = UserVideo.get_for_video_and_user_data(video, UserData.current())

        awarded_points = 0
        if user_video:
            awarded_points = user_video.points

        subtitles_key_name = VideoSubtitles.get_key_name('en', video.youtube_id)
        subtitles = VideoSubtitles.get_by_key_name(subtitles_key_name)
        subtitles_json = None
        show_interactive_transcript = False
        if subtitles:
            subtitles_json = subtitles.load_json()
            transcript_alternative = InteractiveTranscriptExperiment.ab_test()
            show_interactive_transcript = (transcript_alternative == InteractiveTranscriptExperiment.SHOW)

        # TODO (tomyedwab): This is ugly; we would rather have these templates client-side.
        import shared_jinja
        player_html = shared_jinja.get().render_template('videoplayer.html',
            user_data=UserData.current(), video_path=video_path, video=video,
            awarded_points=awarded_points, video_points_base=consts.VIDEO_POINTS_BASE,
            subtitles_json=subtitles_json, show_interactive_transcript=show_interactive_transcript)

        discussion_html = shared_jinja.get().render_template('videodiscussion.html',
            user_data=UserData.current(), video=video, topic=topic, **discussion_options)

        subtitles_html = shared_jinja.get().render_template('videosubtitles.html',
            subtitles_json=subtitles_json)

        return {
            'title': video.title,
            'extra_properties': video.extra_properties or {},
            'description': video.description,
            'youtube_id': video.youtube_id,
            'readable_id': video.readable_id,
            'key': video.key(),
            'video_path': video_path,
            'button_top_exercise': button_top_exercise,
            'related_exercises': [], # disabled for now
            'previous_video': previous_video_dict,
            'next_video': next_video_dict,
            'selected_nav_link': 'watch',
            'issue_labels': ('Component-Videos,Video-%s' % readable_id),
            'author_profile': 'https://plus.google.com/103970106103092409324',
            'player_html': player_html,
            'discussion_html': discussion_html,
            'subtitles_html': subtitles_html,
            'videoPoints': awarded_points,
        }

class Playlist(Searchable, db.Model):

    youtube_id = db.StringProperty()
    url = db.StringProperty()
    title = db.StringProperty()
    description = db.TextProperty()
    readable_id = db.StringProperty() #human readable, but unique id that can be used in URLS
    tags = db.StringListProperty()
    INDEX_ONLY = ['title', 'description']
    INDEX_TITLE_FROM_PROP = 'title'
    INDEX_USES_MULTI_ENTITIES = False

    _serialize_blacklist = ["readable_id"]

    @property
    def ka_url(self):
        return util.absolute_url(self.relative_url)

    @property
    def relative_url(self):
        return '#%s' % urllib.quote(slugify(self.title.lower()))

    @staticmethod
    def get_for_all_topics():
        return filter(lambda playlist: playlist.title in all_topics_list,
                Playlist.all().fetch(1000))

    def get_videos(self):
        video_query = Video.all()
        video_query.filter('playlists = ', self.title)
        video_key_dict = Video.get_dict(video_query, lambda video: video.key())

        video_playlist_query = VideoPlaylist.all()
        video_playlist_query.filter('playlist =', self)
        video_playlist_query.filter('live_association =', True)
        video_playlist_key_dict = VideoPlaylist.get_key_dict(video_playlist_query)
        if not video_playlist_key_dict.has_key(self.key()):
            return []
        video_playlists = sorted(video_playlist_key_dict[self.key()].values(), key=lambda video_playlist: video_playlist.video_position)

        videos = []
        for video_playlist in video_playlists:
            video = video_key_dict[VideoPlaylist.video.get_value_for_datastore(video_playlist)]
            video.position = video_playlist.video_position
            videos.append(video)

        return videos

    def get_video_count(self):
        video_playlist_query = VideoPlaylist.all()
        video_playlist_query.filter('playlist =', self)
        video_playlist_query.filter('live_association =', True)
        return video_playlist_query.count()

class UserPlaylist(db.Model):
    user = db.UserProperty()
    playlist = db.ReferenceProperty(Playlist)
    seconds_watched = db.IntegerProperty(default=0)
    last_watched = db.DateTimeProperty(auto_now_add=True)
    title = db.StringProperty(indexed=False)

    @staticmethod
    def get_for_user_data(user_data):
        query = UserPlaylist.all()
        query.filter('user =', user_data.user)
        return query

    @staticmethod
    def get_key_name(playlist, user_data):
        return user_data.key_email + ":" + playlist.youtube_id

    @staticmethod
    def get_for_playlist_and_user_data(playlist, user_data, insert_if_missing=False):
        if not user_data:
            return None

        key = UserPlaylist.get_key_name(playlist, user_data)

        if insert_if_missing:
            return UserPlaylist.get_or_insert(
                        key_name=key,
                        user=user_data.user,
                        playlist=playlist)
        else:
            return UserPlaylist.get_by_key_name(key)

# No longer depends on the Playlist model; currently used only with Topics
class UserTopic(db.Model):
    user = db.UserProperty()
    seconds_watched = db.IntegerProperty(default=0)
    seconds_migrated = db.IntegerProperty(default=0) # can remove after migration
    last_watched = db.DateTimeProperty(auto_now_add=True)
    topic_key_name = db.StringProperty()
    title = db.StringProperty(indexed=False)

    @staticmethod
    def get_for_user_data(user_data):
        query = UserPlaylist.all()
        query.filter('user =', user_data.user)
        return query

    @staticmethod
    def get_key_name(topic, user_data):
        return user_data.key_email + ":" + topic.key().name()

    @staticmethod
    def get_for_topic_and_user_data(topic, user_data, insert_if_missing=False):
        if not user_data:
            return None

        key = UserTopic.get_key_name(topic, user_data)

        if insert_if_missing:
            return UserTopic.get_or_insert(
                        key_name=key,
                        title=topic.standalone_title,
                        topic_key_name=topic.key().name(),
                        user=user_data.user)
        else:
            return UserTopic.get_by_key_name(key)

    # temporary function used for backfill
    @staticmethod
    def get_for_topic_and_user(topic, user, insert_if_missing=False):
        if not user:
            return None

        key = user.email() + ":" + topic.key().name()

        if insert_if_missing:
            return UserTopic.get_or_insert(
                        key_name=key,
                        title=topic.standalone_title,
                        topic_key_name=topic.key().name(),
                        user=user)
        else:
            return UserTopic.get_by_key_name(key)

class UserVideo(db.Model):

    @staticmethod
    def get_key_name(video_or_youtube_id, user_data):
        id = video_or_youtube_id
        if type(id) not in [str, unicode]:
            id = video_or_youtube_id.youtube_id
        return user_data.key_email + ":" + id

    @staticmethod
    def get_for_video_and_user_data(video, user_data, insert_if_missing=False):
        if not user_data:
            return None
        key = UserVideo.get_key_name(video, user_data)

        if insert_if_missing:
            return UserVideo.get_or_insert(
                        key_name=key,
                        user=user_data.user,
                        video=video,
                        duration=video.duration)
        else:
            return UserVideo.get_by_key_name(key)

    @staticmethod
    def count_completed_for_user_data(user_data):
        return UserVideo.get_completed_user_videos(user_data).count(limit=10000)

    @staticmethod
    def get_completed_user_videos(user_data):
        query = UserVideo.all()
        query.filter("user =", user_data.user)
        query.filter("completed =", True)
        return query

    user = db.UserProperty()
    video = db.ReferenceProperty(Video)

    # Most recently watched second in video (playhead state)
    last_second_watched = db.IntegerProperty(default=0, indexed=False)

    # Number of seconds actually spent watching this video, regardless of jumping around to various
    # scrubber positions. This value can exceed the total duration of the video if it is watched
    # many times, and it doesn't necessarily match the percent watched.
    seconds_watched = db.IntegerProperty(default=0)

    last_watched = db.DateTimeProperty(auto_now_add=True)
    duration = db.IntegerProperty(default=0, indexed=False)
    completed = db.BooleanProperty(default=False)

    @property
    def points(self):
        return points.VideoPointCalculator(self)

    @property
    def progress(self):
        if self.completed:
            return 1.0
        elif self.duration <= 0:
            logging.error("UserVideo.duration has invalid value %r, key: %s" % (self.duration, str(self.key())))
            return 0.0
        else:
            return min(1.0, float(self.seconds_watched) / self.duration)

    @classmethod
    def from_json(cls, json, user_data):
        '''This method exists for testing convenience only. It's called only
        by code that runs in exclusively in development mode. Do not rely on
        this method in production code. If you need to break this code to
        implement some new feature, feel free!
        '''
        readable_id = json['video']['readable_id']
        video = Video.get_for_readable_id(readable_id)

        return cls(
            key_name=UserVideo.get_key_name(video, user_data),
            user=user_data.user,
            video=video,
            last_watched=util.parse_iso8601(json['last_watched']),
            last_second_watched=int(json['last_second_watched']),
            seconds_watched=int(json['seconds_watched']),
            duration=int(json['duration']),
            completed=bool(json['completed'])
        )

class VideoLog(BackupModel):
    user = db.UserProperty()
    video = db.ReferenceProperty(Video)
    video_title = db.StringProperty(indexed=False)

    # Use youtube_id since readable_id may have changed
    # by the time this VideoLog is retrieved
    youtube_id = db.StringProperty(indexed=False)

    # The timestamp corresponding to when this entry was created.
    time_watched = db.DateTimeProperty(auto_now_add=True)
    seconds_watched = db.IntegerProperty(default=0, indexed=False)

    # Most recently watched second in video (playhead state)
    last_second_watched = db.IntegerProperty(indexed=False)
    points_earned = db.IntegerProperty(default=0, indexed=False)
    playlist_titles = db.StringListProperty(indexed=False)

    # Indicates whether or not the video is deemed "complete" by the user.
    # This does not mean that this particular log was the one that resulted
    # in the completion - just that the video has been complete at some point.
    is_video_completed = db.BooleanProperty(indexed=False)

    _serialize_blacklist = ["video"]

    @staticmethod
    def get_for_user_data_between_dts(user_data, dt_a, dt_b):
        query = VideoLog.all()
        query.filter('user =', user_data.user)

        query.filter('time_watched >=', dt_a)
        query.filter('time_watched <=', dt_b)
        query.order('time_watched')

        return query

    @staticmethod
    def get_for_user_data_and_video(user_data, video):
        query = VideoLog.all()

        query.filter('user =', user_data.user)
        query.filter('video =', video)

        query.order('time_watched')

        return query

    @staticmethod
    def add_entry(user_data, video, seconds_watched, last_second_watched, detect_cheat=True):

        user_video = UserVideo.get_for_video_and_user_data(video, user_data, insert_if_missing=True)

        # Cap seconds_watched at duration of video
        seconds_watched = max(0, min(seconds_watched, video.duration))

        video_points_previous = points.VideoPointCalculator(user_video)

        action_cache = last_action_cache.LastActionCache.get_for_user_data(user_data)

        last_video_log = action_cache.get_last_video_log()

        # If the last video logged is not this video and the times being credited
        # overlap, don't give points for this video. Can only get points for one video
        # at a time.
        if (detect_cheat and
                last_video_log and
                last_video_log.key_for_video() != video.key()):
            dt_now = datetime.datetime.now()
            other_video_time = last_video_log.time_watched
            this_video_time = dt_now - datetime.timedelta(seconds=seconds_watched)
            if other_video_time > this_video_time:
                logging.warning("Detected overlapping video logs " +
                                "(user may be watching multiple videos?)")
                return (None, None, 0, False)

        video_log = VideoLog()
        video_log.user = user_data.user
        video_log.video = video
        video_log.video_title = video.title
        video_log.youtube_id = video.youtube_id
        video_log.seconds_watched = seconds_watched
        video_log.last_second_watched = last_second_watched

        if seconds_watched > 0:

            if user_video.seconds_watched == 0:
                user_data.uservideocss_version += 1
                UserVideoCss.set_started(user_data, user_video.video, user_data.uservideocss_version)

            user_video.seconds_watched += seconds_watched
            user_data.total_seconds_watched += seconds_watched

            # Update seconds_watched of all associated topics
            video_topics = db.get(video.topic_string_keys)

            first_topic = True
            for topic in video_topics:
                user_topic = UserTopic.get_for_topic_and_user_data(topic, user_data, insert_if_missing=True)
                user_topic.title = topic.standalone_title
                user_topic.seconds_watched += seconds_watched
                user_topic.last_watched = datetime.datetime.now()
                user_topic.put()

                video_log.playlist_titles.append(user_topic.title)

                if first_topic:
                    action_cache.push_video_log(video_log)

                util_badges.update_with_user_topic(
                        user_data,
                        user_topic,
                        include_other_badges=first_topic,
                        action_cache=action_cache)

                first_topic = False

        user_video.last_second_watched = last_second_watched
        user_video.last_watched = datetime.datetime.now()
        user_video.duration = video.duration

        user_data.record_activity(user_video.last_watched)

        video_points_total = points.VideoPointCalculator(user_video)
        video_points_received = video_points_total - video_points_previous

        just_finished_video = False
        if not user_video.completed and video_points_total >= consts.VIDEO_POINTS_BASE:
            just_finished_video = True
            user_video.completed = True
            user_data.videos_completed = -1

            user_data.uservideocss_version += 1
            UserVideoCss.set_completed(user_data, user_video.video, user_data.uservideocss_version)

            bingo([
                'videos_finished',
                'struggling_videos_finished',
            ])
        video_log.is_video_completed = user_video.completed

        goals_updated = GoalList.update_goals(user_data,
            lambda goal: goal.just_watched_video(user_data, user_video, just_finished_video))

        if video_points_received > 0:
            video_log.points_earned = video_points_received
            user_data.add_points(video_points_received)

        db.put([user_video, user_data])

        # Defer the put of VideoLog for now, as we think it might be causing hot tablets
        # and want to shift it off to an automatically-retrying task queue.
        # http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
        deferred.defer(commit_video_log, video_log,
                       _queue="video-log-queue",
                       _url="/_ah/queue/deferred_videolog")


        if user_data is not None and user_data.coaches:
            # Making a separate queue for the log summaries so we can clearly see how much they are getting used
            deferred.defer(commit_log_summary_coaches, video_log, user_data.coaches,
                _queue="log-summary-queue",
                _url="/_ah/queue/deferred_log_summary")

        return (user_video, video_log, video_points_total, goals_updated)

    def time_started(self):
        return self.time_watched - datetime.timedelta(seconds=self.seconds_watched)

    def time_ended(self):
        return self.time_watched

    def minutes_spent(self):
        return util.minutes_between(self.time_started(), self.time_ended())

    def key_for_video(self):
        return VideoLog.video.get_value_for_datastore(self)

    @classmethod
    def from_json(cls, json, video, user=None):
        '''This method exists for testing convenience only. It's called only
        by code that runs in exclusively in development mode. Do not rely on
        this method in production code. If you need to break this code to
        implement some new feature, feel free!
        '''
        user = user or users.User(json['user'])
        return cls(
            user=user,
            video=video,
            video_title=json['video_title'],
            time_watched=util.parse_iso8601(json['time_watched']),
            seconds_watched=int(json['seconds_watched']),
            last_second_watched=int(json['last_second_watched']),
            points_earned=int(json['points_earned']),
            playlist_titles=json['playlist_titles']
        )

# commit_video_log is used by our deferred video log insertion process
def commit_video_log(video_log, user_data=None):
    video_log.put()

class DailyActivityLog(db.Model):
    """ A log entry for a dashboard presented to users and coaches.

    This is used in the end-user-visible dashboards that display
    student activity and breaks down where the user is spending her time.

    """

    user = db.UserProperty()
    date = db.DateTimeProperty()
    activity_summary = object_property.ObjectProperty()

    @staticmethod
    def get_key_name(user_data, date):
        return "%s:%s" % (user_data.key_email, date.strftime("%Y-%m-%d-%H"))

    @staticmethod
    def build(user_data, date, activity_summary):
        log = DailyActivityLog(key_name=DailyActivityLog.get_key_name(user_data, date))
        log.user = user_data.user
        log.date = date
        log.activity_summary = activity_summary
        return log

    @staticmethod
    def get_for_user_data_between_dts(user_data, dt_a, dt_b):
        query = DailyActivityLog.all()
        query.filter('user =', user_data.user)

        query.filter('date >=', dt_a)
        query.filter('date <', dt_b)
        query.order('date')

        return query

class LogSummaryTypes:
    USER_ADJACENT_ACTIVITY = "UserAdjacentActivity"
    CLASS_DAILY_ACTIVITY = "ClassDailyActivity"

# Tracks the number of shards for each named log summary
class LogSummaryShardConfig(db.Model):
    name = db.StringProperty(required=True)
    num_shards = db.IntegerProperty(required=True, default=1)

    @staticmethod
    def increase_shards(name, num):
        """Increase the number of shards for a given sharded counter.
        Will never decrease the number of shards.

        Parameters:
        name - The name of the counter
        num - How many shards to use

        """
        config = LogSummaryShardConfig.get_or_insert(name, name=name)
        def txn():
            if config.num_shards < num:
                config.num_shards = num
                config.put()

        db.run_in_transaction(txn)

# can keep a variety of different types of summaries pulled from the logs
class LogSummary(db.Model):
    user = db.UserProperty()
    start = db.DateTimeProperty()
    end = db.DateTimeProperty()
    summary_type = db.StringProperty()
    summary = object_property.UnvalidatedObjectProperty()
    name = db.StringProperty(required=True)

    @staticmethod
    def get_start_of_period(activity, delta):
        date = activity.time_started()

        if delta == 1440:
            return datetime.datetime(date.year, date.month, date.day)

        if delta == 60:
            return datetime.datetime(date.year, date.month, date.day, date.hour)

        raise Exception("unhandled delta to get_key_name")

    @staticmethod
    def get_end_of_period(activity, delta):
        return LogSummary.get_start_of_period(activity, delta) + datetime.timedelta(minutes=delta)

    @staticmethod
    def get_name(user_data, summary_type, activity, delta):
        return LogSummary.get_name_by_dates(user_data, summary_type, LogSummary.get_start_of_period(activity, delta), LogSummary.get_end_of_period(activity, delta))

    @staticmethod
    def get_name_by_dates(user_data, summary_type, start, end):
        return "%s:%s:%s:%s" % (user_data.key_email, summary_type, start.strftime("%Y-%m-%d-%H-%M"), end.strftime("%Y-%m-%d-%H-%M"))

    # activity needs to have activity.time_started() and activity.time_done() functions
    # summary_class needs to have a method .add(activity)
    # delta is a time period in minutes
    @staticmethod
    def add_or_update_entry(user_data, activity, summary_class, summary_type, delta=30):

        if user_data is None:
            return

        def txn(name, shard_name, user_data, activities, summary_class, summary_type, delta):
                log_summary = LogSummary.get_by_key_name(shard_name)

                if log_summary is None:
                    activity = activities[0]

                    log_summary = LogSummary(key_name=shard_name, \
                                             name=name, \
                                             user=user_data.user, \
                                             start=LogSummary.get_start_of_period(activity, delta), \
                                             end=LogSummary.get_end_of_period(activity, delta), \
                                             summary_type=summary_type)

                    log_summary.summary = summary_class()

                for activity in activities:
                    log_summary.summary.add(user_data, activity)

                log_summary.put()


        # if activities is a list, we assume all activities belong to the same period - this is used in classtime.fill_class_summaries_from_logs()
        if type(activity) == list:
            activities = activity
            activity = activities[0]
        else:
            activities = [activity]

        name = LogSummary.get_name(user_data, summary_type, activity, delta)
        config = LogSummaryShardConfig.get_or_insert(name, name=name)

        index = random.randrange(config.num_shards)
        shard_name = str(index) + ":" + name


        # running function within a transaction because time might elapse between the get and the put
        # and two processes could get before either puts. Transactions will ensure that its mutually exclusive
        # since they are operating on the same entity
        try:
            db.run_in_transaction(txn, name, shard_name, user_data, activities, summary_class, summary_type, delta)
        except TransactionFailedError:
            # if it is a transaction lock
            logging.info("increasing the number of shards to %i log summary: %s" % (config.num_shards + 1, name))
            LogSummaryShardConfig.increase_shards(name, config.num_shards + 1)
            shard_name = str(config.num_shards) + ":" + name
            db.run_in_transaction(txn, name, shard_name, user_data, activities, summary_class, summary_type, delta)

    @staticmethod
    def get_by_name(name):
        query = LogSummary.all()
        query.filter('name =', name)
        return query

# commit_log_summary is used by our deferred log summary insertion process
def commit_log_summary(activity_log, user_data):
    if user_data is not None:
        from classtime import  ClassDailyActivitySummary # putting this at the top would get a circular reference
        for coach in user_data.coaches:
            LogSummary.add_or_update_entry(UserData.get_from_db_key_email(coach), activity_log, ClassDailyActivitySummary, LogSummaryTypes.CLASS_DAILY_ACTIVITY, 1440)

# commit_log_summary is used by our deferred log summary insertion process
def commit_log_summary_coaches(activity_log, coaches):
    from classtime import  ClassDailyActivitySummary # putting this at the top would get a circular reference
    for coach in coaches:
        LogSummary.add_or_update_entry(UserData.get_from_db_key_email(coach), activity_log, ClassDailyActivitySummary, LogSummaryTypes.CLASS_DAILY_ACTIVITY, 1440)

class ProblemLog(BackupModel):

    user = db.UserProperty()
    exercise = db.StringProperty()
    correct = db.BooleanProperty(default=False)
    time_done = db.DateTimeProperty(auto_now_add=True)
    time_taken = db.IntegerProperty(default=0, indexed=False)
    hint_time_taken_list = db.ListProperty(int, indexed=False)
    hint_after_attempt_list = db.ListProperty(int, indexed=False)
    count_hints = db.IntegerProperty(default=0, indexed=False)
    problem_number = db.IntegerProperty(default=-1) # Used to reproduce problems
    hint_used = db.BooleanProperty(default=False, indexed=False)
    points_earned = db.IntegerProperty(default=0, indexed=False)
    earned_proficiency = db.BooleanProperty(default=False) # True if proficiency was earned on this problem
    suggested = db.BooleanProperty(default=False) # True if the exercise was suggested to the user

    # True if the problem was done while in review mode
    review_mode = db.BooleanProperty(default=False, indexed=False)

    # True if the problem was done while in context-switching topic mode
    topic_mode = db.BooleanProperty(default=False, indexed=False)

    sha1 = db.StringProperty(indexed=False)
    seed = db.StringProperty(indexed=False)
    problem_type = db.StringProperty(indexed=False)
    count_attempts = db.IntegerProperty(default=0, indexed=False)
    time_taken_attempts = db.ListProperty(int, indexed=False)
    attempts = db.StringListProperty(indexed=False)
    random_float = db.FloatProperty() # Add a random float in [0, 1) for easy random sampling
    ip_address = db.StringProperty(indexed=False)

    @classmethod
    def key_for(cls, user_data, exid, problem_number):
        return "problemlog_%s_%s_%s" % (user_data.key_email, exid,
            problem_number)

    @classmethod
    def from_json(cls, json, user_data, exercise):
        '''This method exists for testing convenience only. It's called only
        by code that runs in exclusively in development mode. Do not rely on
        this method in production code. If you need to break this code to
        implement some new feature, feel free!
        '''
        problem_number = int(json['problem_number'])
        return cls(
            attempts=json['attempts'],
            correct=bool(json['correct']),
            count_attempts=int(json['count_attempts']),
            count_hints=int(json['count_hints']),
            earned_proficiency=bool(json['earned_proficiency']),
            exercise=exercise.name,
            hint_after_attempt_list=json['hint_after_attempt_list'],
            hint_time_taken_list=json['hint_time_taken_list'],
            hint_used=bool(json['hint_used']),
            ip_address=json['ip_address'],
            key_name=cls.key_for(user_data, exercise.name, problem_number),
            points_earned=int(json['points_earned']),
            problem_number=problem_number,
            problem_type=json['problem_type'],
            random_float=json['random_float'],
            review_mode=bool(json['review_mode']),
            seed=json['seed'],
            sha1=json['sha1'],
            suggested=bool(json['suggested']),
            time_done=util.parse_iso8601(json['time_done']),
            time_taken=int(json['time_taken']),
            time_taken_attempts=json['time_taken_attempts'],
            user=user_data.user,
        )

    def put(self):
        if self.random_float is None:
            self.random_float = random.random()
        db.Model.put(self)

    @property
    def ka_url(self):
        return util.absolute_url("/exercise/%s?problem_number=%s" % \
            (self.exercise, self.problem_number))

    @staticmethod
    def get_for_user_data_between_dts(user_data, dt_a, dt_b):
        query = ProblemLog.all()
        query.filter('user =', user_data.user)

        query.filter('time_done >=', dt_a)
        query.filter('time_done <', dt_b)

        query.order('time_done')

        return query

    def time_taken_capped_for_reporting(self):
        # For reporting's sake, we cap the amount of time that you can be considered to be
        # working on a single problem at 60 minutes. If you've left your browser open
        # longer, you're probably not actively working on the problem.
        return min(consts.MAX_WORKING_ON_PROBLEM_SECONDS, self.time_taken)

    def time_started(self):
        return self.time_done - datetime.timedelta(seconds=self.time_taken_capped_for_reporting())

    def time_ended(self):
        return self.time_done

    def minutes_spent(self):
        return util.minutes_between(self.time_started(), self.time_ended())

# commit_problem_log is used by our deferred problem log insertion process
def commit_problem_log(problem_log_source, user_data=None):
    try:
        if not problem_log_source or not problem_log_source.key().name:
            logging.critical("Skipping problem log commit due to missing problem_log_source or key().name")
            return
    except db.NotSavedError:
        # Handle special case during new exercise deploy
        logging.critical("Skipping problem log commit due to db.NotSavedError")
        return

    if problem_log_source.count_attempts > 1000:
        logging.info("Ignoring attempt to write problem log w/ attempts over 1000.")
        return

    # This does not have the same behavior as .insert(). This is used because
    # tasks can be run out of order so we extend the list as needed and insert
    # values.
    def insert_in_position(index, items, val, filler):
        if index >= len(items):
            items.extend([filler] * (index + 1 - len(items)))
        items[index] = val

    # Committing transaction combines existing problem log with any followup attempts
    def txn():
        problem_log = ProblemLog.get_by_key_name(problem_log_source.key().name())

        if not problem_log:
            problem_log = ProblemLog(
                key_name = problem_log_source.key().name(),
                user = problem_log_source.user,
                exercise = problem_log_source.exercise,
                problem_number = problem_log_source.problem_number,
                time_done = problem_log_source.time_done,
                sha1 = problem_log_source.sha1,
                seed = problem_log_source.seed,
                problem_type = problem_log_source.problem_type,
                suggested = problem_log_source.suggested,
                ip_address = problem_log_source.ip_address,
                review_mode = problem_log_source.review_mode,
                topic_mode = problem_log_source.topic_mode,
        )

        problem_log.count_hints = max(problem_log.count_hints, problem_log_source.count_hints)
        problem_log.hint_used = problem_log.count_hints > 0
        index_attempt = max(0, problem_log_source.count_attempts - 1)

        # Bump up attempt count
        if problem_log_source.attempts[0] != "hint": # attempt
            if index_attempt < len(problem_log.time_taken_attempts) \
               and problem_log.time_taken_attempts[index_attempt] != -1:
                # This attempt has already been logged. Ignore this dupe taskqueue execution.
                logging.info("Skipping problem log commit due to dupe taskqueue\
                    execution for attempt: %s, key.name: %s" % \
                    (index_attempt, problem_log_source.key().name()))
                return

            problem_log.count_attempts += 1

            # Add time_taken for this individual attempt
            problem_log.time_taken += problem_log_source.time_taken
            insert_in_position(index_attempt, problem_log.time_taken_attempts, problem_log_source.time_taken, filler= -1)

            # Add actual attempt content
            insert_in_position(index_attempt, problem_log.attempts, problem_log_source.attempts[0], filler="")

            # Proficiency earned should never change per problem
            problem_log.earned_proficiency = problem_log.earned_proficiency or \
                problem_log_source.earned_proficiency

        else: # hint
            index_hint = max(0, problem_log_source.count_hints - 1)

            if index_hint < len(problem_log.hint_time_taken_list) \
               and problem_log.hint_time_taken_list[index_hint] != -1:
                # This attempt has already been logged. Ignore this dupe taskqueue execution.
                return

            # Add time taken for hint
            insert_in_position(index_hint, problem_log.hint_time_taken_list, problem_log_source.time_taken, filler= -1)

            # Add attempt number this hint follows
            insert_in_position(index_hint, problem_log.hint_after_attempt_list, problem_log_source.count_attempts, filler= -1)

        # Points should only be earned once per problem, regardless of attempt count
        problem_log.points_earned = max(problem_log.points_earned, problem_log_source.points_earned)

        # Correct cannot be changed from False to True after first attempt
        problem_log.correct = (problem_log_source.count_attempts == 1 or problem_log.correct) and problem_log_source.correct and not problem_log.count_hints

        logging.info(problem_log.time_ended())
        problem_log.put()


    db.run_in_transaction(txn)

# Represents a matching between a playlist and a video
# Allows us to keep track of which videos are in a playlist and
# which playlists a video belongs to (not 1-to-1 mapping)
class VideoPlaylist(db.Model):

    playlist = db.ReferenceProperty(Playlist)
    video = db.ReferenceProperty(Video)
    video_position = db.IntegerProperty()

    # Lets us enable/disable video playlist relationships in bulk without removing the entry
    live_association = db.BooleanProperty(default=False)
    last_live_association_generation = db.IntegerProperty(default=0)

    _VIDEO_PLAYLIST_KEY_FORMAT = "VideoPlaylist_Videos_for_Playlist_%s"
    _PLAYLIST_VIDEO_KEY_FORMAT = "VideoPlaylist_Playlists_for_Video_%s"

    @staticmethod
    def get_namespace():
        return "%s_%s" % (App.version, Setting.topic_tree_version())

    @staticmethod
    def get_cached_videos_for_playlist(playlist, limit=500):

        key = VideoPlaylist._VIDEO_PLAYLIST_KEY_FORMAT % playlist.key()
        namespace = VideoPlaylist.get_namespace()

        videos = memcache.get(key, namespace=namespace)

        if not videos:
            query = VideoPlaylist.all()
            query.filter('playlist =', playlist)
            query.filter('live_association = ', True)
            query.order('video_position')
            videos = [video_playlist.video for video_playlist in query.fetch(limit)]

            memcache.set(key, videos, namespace=namespace)

        return videos

    @staticmethod
    def get_cached_playlists_for_video(video, limit=5):

        key = VideoPlaylist._PLAYLIST_VIDEO_KEY_FORMAT % video.key()
        namespace = VideoPlaylist.get_namespace()

        playlists = memcache.get(key, namespace=namespace)

        if playlists is None:
            query = VideoPlaylist.all()
            query.filter('video =', video)
            query.filter('live_association = ', True)
            playlists = [video_playlist.playlist for video_playlist in query.fetch(limit)]

            memcache.set(key, playlists, namespace=namespace)

        return playlists

    @staticmethod
    def get_query_for_playlist_title(playlist_title):
        query = Playlist.all()
        query.filter('title =', playlist_title)
        playlist = query.get()
        query = VideoPlaylist.all()
        query.filter('playlist =', playlist)
        query.filter('live_association = ', True) # need to change this to true once I'm done with all of my hacks
        query.order('video_position')
        return query

    @staticmethod
    def get_key_dict(query):
        video_playlist_key_dict = {}
        for video_playlist in query.fetch(10000):
            playlist_key = VideoPlaylist.playlist.get_value_for_datastore(video_playlist)

            if not video_playlist_key_dict.has_key(playlist_key):
                video_playlist_key_dict[playlist_key] = {}

            video_playlist_key_dict[playlist_key][VideoPlaylist.video.get_value_for_datastore(video_playlist)] = video_playlist

        return video_playlist_key_dict

class ExerciseVideo(db.Model):

    video = db.ReferenceProperty(Video)
    exercise = db.ReferenceProperty(Exercise)
    exercise_order = db.IntegerProperty() # the order videos should appear for this exercise

    def key_for_video(self):
        return ExerciseVideo.video.get_value_for_datastore(self)

    @staticmethod
    def get_key_dict(query):
        exercise_video_key_dict = {}
        for exercise_video in query.fetch(10000):
            video_key = ExerciseVideo.video.get_value_for_datastore(exercise_video)

            if not exercise_video_key_dict.has_key(video_key):
                exercise_video_key_dict[video_key] = {}

            exercise_video_key_dict[video_key][ExerciseVideo.exercise.get_value_for_datastore(exercise_video)] = exercise_video

        return exercise_video_key_dict

    # returns all ExerciseVideo objects whose Video has no topic
    @staticmethod
    def get_all_with_topicless_videos(version=None):
        videos = Video.get_all_live(version)
        video_keys = [v.key() for v in videos]
        evs = ExerciseVideo.all().fetch(100000)

        if version is None or version.default:
            return [ev for ev in evs
                    if ExerciseVideo.video.get_value_for_datastore(ev)
                    not in video_keys]

        # if there is a version check to see if there are any updates to the exercise videos
        else:
            video_dict = dict((v.key(), v.readable_id) for v in videos)
            video_readable_dict = dict((v.readable_id, v) for v in videos)
            ev_key_dict = dict((ev.key(), ev) for ev in evs)

            # create ev_dict so we can access the ev in constant time from the exercise_key and the video_readable_id
            ev_dict = {}

            for ev in evs:
                exercise_key = ExerciseVideo.exercise.get_value_for_datastore(ev)
                video_key = ExerciseVideo.video.get_value_for_datastore(ev)

                # if the video is not live get it (it will be a topicless video)
                # there shouldnt be too many of these, hence not bothering to do
                # things efficiently in one get
                if video_key not in video_dict:
                    video = db.get(video_key)
                    video_readable_id = video.readable_id
                    video_readable_dict[video.readable_id] = video
                else:
                    video_readable_id = video_dict[video_key]
                    video = video_readable_dict[video_readable_id]

                # the following line is needed otherwise the list comprehension
                # by the return statement will fail on the un put EVs with:
                # Key' object has no attribute '_video' if
                # ExerciseVideo.video.get_value_for_datastore(ev) is used
                ev.video = video

                if exercise_key not in ev_dict:
                    ev_dict[exercise_key] = {}

                ev_dict[exercise_key][video_readable_id] = ev.key()

            # cycle through all the version changes to see if an exercise has been updated
            changes = VersionContentChange.get_updated_content_dict(version)
            new_evs = []

            for key, content in changes.iteritems():

                if (type(content) == Exercise):

                    # remove the existing Exercise_Videos if there are any
                    if key in ev_dict:
                        for video_readable_id, ev_key in ev_dict[key].iteritems():
                            del ev_key_dict[ev_key]

                    # add new related_videos
                    for i, video_readable_id in enumerate(content.related_videos
                        if hasattr(content, "related_videos") else []):

                        if video_readable_id not in video_readable_dict:
                            video = video.get_for_readable_id(video_readable_id)
                            video_readable_dict[video_readable_id] = (
                                video.readable_id)
                        else:
                            video = video_readable_dict[video_readable_id]

                        new_ev = ExerciseVideo(
                            video=video,
                            exercise=content,
                            exercise_order=i
                            )
                        new_evs.append(new_ev)

            evs = [ev for ev in ev_key_dict.values()]
            evs += new_evs

            # ExerciseVideo.video.get_value_for_datastore(ev) is not needed
            # because we populated ev.video
            return [ev for ev in evs if ev.video.key() not in video_keys]


class UserExerciseCache(db.Model):
    """ UserExerciseCache is an optimized-for-read-and-deserialization cache of
    user-specific exercise states.
    It can be reconstituted at any time via UserExercise objects.

    """

    # Bump this whenever you change the structure of the cached UserExercises
    # and need to invalidate all old caches
    CURRENT_VERSION = 9

    version = db.IntegerProperty()
    dicts = object_property.UnvalidatedObjectProperty()

    def user_exercise_dict(self, exercise_name):
        return self.dicts.get(exercise_name) or UserExerciseCache.dict_from_user_exercise(None)

    def update(self, user_exercise):
        self.dicts[user_exercise.exercise] = UserExerciseCache.dict_from_user_exercise(user_exercise)

    @staticmethod
    def key_for_user_data(user_data):
        return "UserExerciseCache:%s" % user_data.key_email

    @staticmethod
    def get(user_data_or_list):
        if not user_data_or_list:
            raise Exception("Must provide UserData when loading UserExerciseCache")

        # We can grab a single UserExerciseCache or do an optimized grab of a bunch of 'em
        user_data_list = user_data_or_list if type(user_data_or_list) == list else [user_data_or_list]

        # Try to get 'em all by key name
        user_exercise_caches = UserExerciseCache.get_by_key_name(
                map(
                    lambda user_data: UserExerciseCache.key_for_user_data(user_data),
                    user_data_list),
                config=db.create_config(read_policy=db.EVENTUAL_CONSISTENCY)
                )

        # For any that are missing or are out of date,
        # build up asynchronous queries to repopulate their data
        async_queries = []
        missing_cache_indices = []
        for i, user_exercise_cache in enumerate(user_exercise_caches):
            if not user_exercise_cache or user_exercise_cache.version != UserExerciseCache.CURRENT_VERSION:
                # Null out the reference so the gc can collect, in case it's
                # a stale version, since we're going to rebuild it below.
                user_exercise_caches[i] = None

                # This user's cached graph is missing or out-of-date,
                # put it in the list of graphs to be regenerated.
                async_queries.append(UserExercise.get_for_user_data(user_data_list[i]))
                missing_cache_indices.append(i)

        if len(async_queries) > 0:
            caches_to_put = []

            # Run the async queries in batches to avoid exceeding memory limits.
            # Some coaches can have lots of active students, and their user
            # exercise information is too much for app engine instances.
            BATCH_SIZE = 5
            for i in range(0, len(async_queries), BATCH_SIZE):
                tasks = util.async_queries(async_queries[i:i + BATCH_SIZE])

                # Populate the missing graphs w/ results from async queries
                for j, task in enumerate(tasks):
                    user_index = missing_cache_indices[i + j]
                    user_data = user_data_list[user_index]
                    user_exercises = task.get_result()

                    user_exercise_cache = UserExerciseCache.generate(user_data, user_exercises)
                    user_exercise_caches[user_index] = user_exercise_cache

                    if len(caches_to_put) < 10:
                        # We only put 10 at a time in case a teacher views a report w/ tons and tons of uncached students
                        caches_to_put.append(user_exercise_cache)

            # Null out references explicitly for GC.
            tasks = None
            async_queries = None

            if len(caches_to_put) > 0:
                # Fire off an asynchronous put to cache the missing results. On the production server,
                # we don't wait for the put to finish before dealing w/ the rest of the request
                # because we don't really care if the cache misses.
                future_put = db.put_async(caches_to_put)

                if App.is_dev_server:
                    # On the dev server, we have to explicitly wait for get_result in order to
                    # trigger the put (not truly asynchronous).
                    future_put.get_result()

        if not user_exercise_caches:
            return []

        # Return list of caches if a list was passed in,
        # otherwise return single cache
        return user_exercise_caches if type(user_data_or_list) == list else user_exercise_caches[0]

    @staticmethod
    def dict_from_user_exercise(user_exercise, struggling_model=None):
        # TODO(david): We can probably remove some of this stuff here.
        return {
                "streak": user_exercise.streak if user_exercise else 0,
                "longest_streak": user_exercise.longest_streak if user_exercise else 0,
                "progress": user_exercise.progress if user_exercise else 0.0,
                "struggling": user_exercise.is_struggling(struggling_model) if user_exercise else False,
                "total_done": user_exercise.total_done if user_exercise else 0,
                "last_done": user_exercise.last_done if user_exercise else datetime.datetime.min,
                "last_review": user_exercise.last_review if user_exercise else datetime.datetime.min,
                "review_interval_secs": user_exercise.review_interval_secs if user_exercise else 0,
                "proficient_date": user_exercise.proficient_date if user_exercise else 0,
                }

    @staticmethod
    def generate(user_data, user_exercises=None):

        if not user_exercises:
            user_exercises = UserExercise.get_for_user_data(user_data)

        current_user = UserData.current()
        is_current_user = current_user and current_user.user_id == user_data.user_id

        # Experiment to try different struggling models.
        # It's important to pass in the user_data of the student owning the
        # exercise, and not of the current viewer (as it may be a coach).
        struggling_model = StrugglingExperiment.get_alternative_for_user(
                user_data, is_current_user) or StrugglingExperiment.DEFAULT

        dicts = {}

        # Build up cache
        for user_exercise in user_exercises:
            user_exercise_dict = UserExerciseCache.dict_from_user_exercise(
                    user_exercise, struggling_model)

            # In case user has multiple UserExercise mappings for a specific exercise,
            # always prefer the one w/ more problems done
            if user_exercise.exercise not in dicts or dicts[user_exercise.exercise]["total_done"] < user_exercise_dict["total_done"]:
                dicts[user_exercise.exercise] = user_exercise_dict

        return UserExerciseCache(
                key_name=UserExerciseCache.key_for_user_data(user_data),
                version=UserExerciseCache.CURRENT_VERSION,
                dicts=dicts,
            )

class UserExerciseGraph(object):

    def __init__(self, graph={}, cache=None):
        self.graph = graph
        self.cache = cache

    def graph_dict(self, exercise_name):
        return self.graph.get(exercise_name)

    def graph_dicts(self):
        return sorted(sorted(self.graph.values(),
                             key=lambda graph_dict: graph_dict["v_position"]),
                             key=lambda graph_dict: graph_dict["h_position"])

    def proficient_exercise_names(self):
        return [graph_dict["name"] for graph_dict in self.proficient_graph_dicts()]

    def suggested_exercise_names(self):
        return [graph_dict["name"] for graph_dict in self.suggested_graph_dicts()]

    def review_exercise_names(self):
        return [graph_dict["name"] for graph_dict in self.review_graph_dicts()]

    def has_completed_review(self):
        # TODO(david): This should return whether the user has completed today's
        #     review session.
        return not self.review_exercise_names()

    def reviews_left_count(self):
        # TODO(david): For future algorithms this should return # reviews left
        #     for today's review session.
        # TODO(david): Make it impossible to have >= 100 reviews.
        return len(self.review_exercise_names())

    def suggested_graph_dicts(self):
        return [graph_dict for graph_dict in self.graph_dicts() if graph_dict["suggested"]]

    def proficient_graph_dicts(self):
        return [graph_dict for graph_dict in self.graph_dicts() if graph_dict["proficient"]]

    def review_graph_dicts(self):
        return [graph_dict for graph_dict in self.graph_dicts() if graph_dict["reviewing"]]

    def recent_graph_dicts(self, n_recent=2):
        return sorted(
                [graph_dict for graph_dict in self.graph_dicts() if graph_dict["last_done"]],
                reverse=True,
                key=lambda graph_dict: graph_dict["last_done"],
                )[0:n_recent]

    @staticmethod
    def mark_reviewing(graph):
        """ Mark to-be-reviewed exercise dicts as reviewing, which is used by the knowledge map
        and the profile page.
        """

        # an exercise ex should be reviewed iff all of the following are true:
        #   * ex and all of ex's covering ancestors either
        #      * are scheduled to have their next review in the past, or
        #      * were answered incorrectly on last review (i.e. streak == 0 with proficient == true)
        #   * none of ex's covering ancestors should be reviewed or ex was
        #     previously incorrectly answered (ex.streak == 0)
        #   * the user is proficient at ex
        # the algorithm:
        #   for each exercise:
        #     traverse it's ancestors, computing and storing the next review time (if not already done),
        #     using now as the next review time if proficient and streak==0
        #   select and mark the exercises in which the user is proficient but with next review times in the past as review candidates
        #   for each of those candidates:
        #     traverse it's ancestors, computing and storing whether an ancestor is also a candidate
        #   all exercises that are candidates but do not have ancestors as
        #   candidates should be listed for review. Covering ancestors are not
        #   considered for incorrectly answered review questions
        #   (streak == 0 and proficient).

        now = datetime.datetime.now()

        def compute_next_review(graph_dict):
            if graph_dict.get("next_review") is None:
                graph_dict["next_review"] = datetime.datetime.min

                if graph_dict["total_done"] > 0 and graph_dict["last_review"] and graph_dict["last_review"] > datetime.datetime.min:
                    next_review = graph_dict["last_review"] + UserExercise.get_review_interval_from_seconds(graph_dict["review_interval_secs"])

                    if next_review > now and graph_dict["proficient"] and graph_dict["streak"] == 0:
                        next_review = now

                    if next_review > graph_dict["next_review"]:
                        graph_dict["next_review"] = next_review

                for covering_graph_dict in graph_dict["coverer_dicts"]:
                    covering_next_review = compute_next_review(covering_graph_dict)
                    if (covering_next_review > graph_dict["next_review"] and
                            graph_dict["streak"] != 0):
                        graph_dict["next_review"] = covering_next_review

            return graph_dict["next_review"]

        def compute_is_ancestor_review_candidate(graph_dict):
            if graph_dict.get("is_ancestor_review_candidate") is None:

                graph_dict["is_ancestor_review_candidate"] = False

                for covering_graph_dict in graph_dict["coverer_dicts"]:
                    graph_dict["is_ancestor_review_candidate"] = (graph_dict["is_ancestor_review_candidate"] or
                            covering_graph_dict["is_review_candidate"] or
                            compute_is_ancestor_review_candidate(covering_graph_dict))

            return graph_dict["is_ancestor_review_candidate"]

        for graph_dict in graph.values():
            graph_dict["reviewing"] = False # Assume false at first
            compute_next_review(graph_dict)

        candidate_dicts = []
        for graph_dict in graph.values():
            if (graph_dict["proficient"] and
                    graph_dict["next_review"] <= now and
                    graph_dict["total_done"] > 0):
                graph_dict["is_review_candidate"] = True
                candidate_dicts.append(graph_dict)
            else:
                graph_dict["is_review_candidate"] = False

        for graph_dict in candidate_dicts:
            if (not compute_is_ancestor_review_candidate(graph_dict) or
                    graph_dict["streak"] == 0):
                graph_dict["reviewing"] = True

    def states(self, exercise_name):
        graph_dict = self.graph_dict(exercise_name)

        return {
            "proficient": graph_dict["proficient"],
            "suggested": graph_dict["suggested"],
            "struggling": graph_dict["struggling"],
            "reviewing": graph_dict["reviewing"]
        }

    @staticmethod
    def current():
        return UserExerciseGraph.get(UserData.current())

    @staticmethod
    def get(user_data_or_list, exercises_allowed=None):
        if not user_data_or_list:
            return [] if type(user_data_or_list) == list else None

        # We can grab a single UserExerciseGraph or do an optimized grab of a bunch of 'em
        user_data_list = user_data_or_list if type(user_data_or_list) == list else [user_data_or_list]
        user_exercise_cache_list = UserExerciseCache.get(user_data_list)

        if not user_exercise_cache_list:
            return [] if type(user_data_or_list) == list else None

        exercise_dicts = UserExerciseGraph.exercise_dicts(exercises_allowed)

        user_exercise_graphs = map(
                lambda (user_data, user_exercise_cache): UserExerciseGraph.generate(user_data, user_exercise_cache, exercise_dicts),
                itertools.izip(user_data_list, user_exercise_cache_list))

        # Return list of graphs if a list was passed in,
        # otherwise return single graph
        return user_exercise_graphs if type(user_data_or_list) == list else user_exercise_graphs[0]

    @staticmethod
    def dict_from_exercise(exercise):
        return {
                "id": exercise.key().id(),
                "name": exercise.name,
                "display_name": exercise.display_name,
                "h_position": exercise.h_position,
                "v_position": exercise.v_position,
                "proficient": None,
                "explicitly_proficient": None,
                "suggested": None,
                "prerequisites": map(lambda exercise_name: {"name": exercise_name, "display_name": Exercise.to_display_name(exercise_name)}, exercise.prerequisites),
                "covers": exercise.covers,
                "live": exercise.live,
            }

    @staticmethod
    def exercise_dicts(exercises_allowed=None):
        return map(
                UserExerciseGraph.dict_from_exercise,
                exercises_allowed or Exercise.get_all_use_cache()
        )

    @staticmethod
    def get_and_update(user_data, user_exercise):
        user_exercise_cache = UserExerciseCache.get(user_data)
        user_exercise_cache.update(user_exercise)
        return UserExerciseGraph.generate(user_data, user_exercise_cache, UserExerciseGraph.exercise_dicts())

    @staticmethod
    def get_boundary_names(graph):
        """ Return the names of the exercises that succeed
        the student's proficient exercises.
        """
        all_exercises_dict = {}

        def is_boundary(graph_dict):
            name = graph_dict["name"]

            if name in all_exercises_dict:
                return all_exercises_dict[name]

            # Don't suggest already-proficient exercises
            if graph_dict["proficient"]:
                all_exercises_dict.update({name: False})
                return False

            # First, assume we're suggesting this exercise
            is_suggested = True

            # Don't suggest exercises that are covered by other suggested exercises
            for covering_graph_dict in graph_dict["coverer_dicts"]:
                if is_boundary(covering_graph_dict):
                    all_exercises_dict.update({name: False})
                    return False

            # Don't suggest exercises if the user isn't proficient in all prerequisites
            for prerequisite_graph_dict in graph_dict["prerequisite_dicts"]:
                if not prerequisite_graph_dict["proficient"]:
                    all_exercises_dict.update({name: False})
                    return False

            all_exercises_dict.update({name: True})
            return True

        boundary_graph_dicts = []
        for exercise_name in graph:
            graph_dict = graph[exercise_name]
            if graph_dict["live"] and is_boundary(graph_dict):
                boundary_graph_dicts.append(graph_dict)

        boundary_graph_dicts = sorted(sorted(boundary_graph_dicts,
                             key=lambda graph_dict: graph_dict["v_position"]),
                             key=lambda graph_dict: graph_dict["h_position"])

        return [graph_dict["name"]
                    for graph_dict in boundary_graph_dicts]

    @staticmethod
    def get_attempted_names(graph):
        """ Return the names of the exercises that the student has attempted.

        Exact details, such as the threshold that marks a real attempt
        or the relevance rankings of attempted exercises, TBD.
        """
        progress_threshold = 0.5

        attempted_graph_dicts = filter(
                                    lambda graph_dict:
                                        (graph_dict["progress"] > progress_threshold
                                            and not graph_dict["proficient"]),
                                    graph.values())

        attempted_graph_dicts = sorted(attempted_graph_dicts,
                            reverse=True,
                            key=lambda graph_dict: graph_dict["progress"])

        return [graph_dict["name"] for graph_dict in attempted_graph_dicts]

    @staticmethod
    def mark_suggested(graph):
        """ Mark 5 exercises as suggested, which are used by the knowledge map
        and the profile page.

        Attempted but not proficient exercises are suggested first,
        then padded with exercises just beyond the proficiency boundary.

        TODO: Although exercises might be marked in a particular order,
        they will always be returned by suggested_graph_dicts()
        sorted by knowledge map position. We might want to change that.
        """
        num_to_suggest = 5
        suggested_names = UserExerciseGraph.get_attempted_names(graph)

        if len(suggested_names) < num_to_suggest:
            boundary_names = UserExerciseGraph.get_boundary_names(graph)
            suggested_names.extend(boundary_names)

        suggested_names = suggested_names[:num_to_suggest]

        for exercise_name in graph:
            is_suggested = exercise_name in suggested_names
            graph[exercise_name]["suggested"] = is_suggested

    @staticmethod
    def generate(user_data, user_exercise_cache, exercise_dicts):

        graph = {}

        # Build up base of graph
        for exercise_dict in exercise_dicts:

            user_exercise_dict = user_exercise_cache.user_exercise_dict(exercise_dict["name"])

            graph_dict = {}

            graph_dict.update(user_exercise_dict)
            graph_dict.update(exercise_dict)
            graph_dict.update({
                "coverer_dicts": [],
                "prerequisite_dicts": [],
            })

            # In case user has multiple UserExercise mappings for a specific exercise,
            # always prefer the one w/ more problems done
            if graph_dict["name"] not in graph or graph[graph_dict["name"]]["total_done"] < graph_dict["total_done"]:
                graph[graph_dict["name"]] = graph_dict

        # Cache coverers and prereqs for later
        for graph_dict in graph.values():
            # Cache coverers
            for covered_exercise_name in graph_dict["covers"]:
                covered_graph_dict = graph.get(covered_exercise_name)
                if covered_graph_dict:
                    covered_graph_dict["coverer_dicts"].append(graph_dict)

            # Cache prereqs
            for prerequisite_exercise_name in graph_dict["prerequisites"]:
                prerequisite_graph_dict = graph.get(prerequisite_exercise_name["name"])
                if prerequisite_graph_dict:
                    graph_dict["prerequisite_dicts"].append(prerequisite_graph_dict)

        # Set explicit proficiencies
        for exercise_name in user_data.proficient_exercises:
            graph_dict = graph.get(exercise_name)
            if graph_dict:
                graph_dict["proficient"] = graph_dict["explicitly_proficient"] = True

        # Calculate implicit proficiencies
        def set_implicit_proficiency(graph_dict):
            if graph_dict["proficient"] is not None:
                return graph_dict["proficient"]

            graph_dict["proficient"] = False

            # Consider an exercise implicitly proficient if the user has
            # never missed a problem and a covering ancestor is proficient
            if graph_dict["streak"] == graph_dict["total_done"]:
                for covering_graph_dict in graph_dict["coverer_dicts"]:
                    if set_implicit_proficiency(covering_graph_dict):
                        graph_dict["proficient"] = True
                        break

            return graph_dict["proficient"]

        for exercise_name in graph:
            set_implicit_proficiency(graph[exercise_name])

        # Calculate suggested and reviewing
        UserExerciseGraph.mark_suggested(graph)
        UserExerciseGraph.mark_reviewing(graph)

        return UserExerciseGraph(graph=graph, cache=user_exercise_cache)

class PromoRecord(db.Model):
    """ A record to mark when a user has viewed a one-time event of some
    sort, such as a promo.

    """

    def __str__(self):
        return self.key().name()

    @staticmethod
    def has_user_seen_promo(promo_name, user_id):
        return PromoRecord.get_for_values(promo_name, user_id) is not None

    @staticmethod
    def get_for_values(promo_name, user_id):
        key_name = PromoRecord._build_key_name(promo_name, user_id)
        return PromoRecord.get_by_key_name(key_name)

    @staticmethod
    def _build_key_name(promo_name, user_id):
        escaped_promo_name = urllib.quote(promo_name)
        escaped_user_id = urllib.quote(user_id)
        return "%s:%s" % (escaped_promo_name, escaped_user_id)

    @staticmethod
    def record_promo(promo_name, user_id, skip_check=False):
        """ Attempt to mark that a user has seen a one-time promotion.
        Returns True if the registration was successful, and returns False
        if the user has already seen that promotion.

        If skip_check is True, it will forcefully create a promo record
        and avoid any checks for existing ones. Use with care.
        """
        key_name = PromoRecord._build_key_name(promo_name, user_id)
        if not skip_check:
            record = PromoRecord.get_by_key_name(key_name)
            if record is not None:
                # Already shown the promo.
                return False
        record = PromoRecord(key_name=key_name)
        record.put()
        return True

class VideoSubtitles(db.Model):
    """Subtitles for a YouTube video

    This is a cache of the content from Universal Subtitles for a video. A job
    runs periodically to keep these up-to-date.

    Store with a key name of "LANG:YOUTUBEID", e.g., "en:9Ek61w1LxSc".
    """
    modified = db.DateTimeProperty(auto_now=True, indexed=False)
    youtube_id = db.StringProperty()
    language = db.StringProperty()
    json = db.TextProperty()

    @staticmethod
    def get_key_name(language, youtube_id):
        return '%s:%s' % (language, youtube_id)

    def load_json(self):
        """Return subtitles JSON as a Python object

        If there is an issue loading the JSON, None is returned.
        """
        try:
            return json.loads(self.json)
        except ValueError:
            logging.warn('VideoSubtitles.load_json: json decode error')

class VideoSubtitlesFetchReport(db.Model):
    """Report on fetching of subtitles from Universal Subtitles

    Jobs that fail or are cancelled from the admin interface leave a hanging
    status since there's no callback to update the report.

    Store with a key name of JOB_NAME. Usually this is the UUID4 used by the
    task chain for processing. The key name is displayed as the report name.
    """
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True, indexed=False)
    status = db.StringProperty(indexed=False)
    fetches = db.IntegerProperty(indexed=False)
    writes = db.IntegerProperty(indexed=False)
    errors = db.IntegerProperty(indexed=False)
    redirects = db.IntegerProperty(indexed=False)
    
class ParentSignup(db.Model):
    """ An entity to collect an interest list for parents interested
    in creating under-13 accounts before the feature is actually ready.
    
    The key_name stores the e-mail.

    """

    pass

from badges import util_badges, last_action_cache, topic_exercise_badges
from phantom_users import util_notify
from goals.models import GoalList
from exercises.file_contents import exercise_sha1

# TODO(kamens): remove this after refactor stabilizes and we won't be rolling back
import models_backwards_compat
