#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from google.appengine.ext import db

import models
from app import App
import request_cache
import layer_cache

class FeedbackType:
    Question="question"
    Answer="answer"
    Comment="comment"

    @staticmethod
    def is_valid(type):
        return (type == FeedbackType.Question or 
                type == FeedbackType.Answer or 
                type == FeedbackType.Comment)

class FeedbackFlag:

    # 2 or more flags immediately hides feedback
    HIDE_LIMIT = 2

    Inappropriate="inappropriate"
    LowQuality="lowquality"
    DoesNotBelong="doesnotbelong"
    Spam="spam"

    @staticmethod
    def is_valid(flag):
        return (flag == FeedbackFlag.Inappropriate or 
                flag == FeedbackFlag.LowQuality or 
                flag == FeedbackFlag.DoesNotBelong or 
                flag == FeedbackFlag.Spam)

class Feedback(db.Model):
    author = db.UserProperty()
    author_user_id = db.StringProperty()
    author_nickname = db.StringProperty()
    content = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    deleted = db.BooleanProperty(default=False)
    targets = db.ListProperty(db.Key) # first element is video key.
                                      # optional second element is question key.
    types = db.StringListProperty()
    is_flagged = db.BooleanProperty(default=False)
    is_hidden_by_flags = db.BooleanProperty(default=False)
    flags = db.StringListProperty(default=None)
    flagged_by = db.StringListProperty(default=None)
    sum_votes = db.IntegerProperty(default=0)
    inner_score = db.FloatProperty(default=0.0)

    @staticmethod
    def cache_key_for_video(video):
        return "videofeedbackcache:%s" % video.key()

    def __init__(self, *args, **kwargs):
        db.Model.__init__(self, *args, **kwargs)
        self.children_cache = [] # For caching each question's answers during render

    def clear_cache_for_video(self):
        layer_cache.ChunkedResult.delete(
            Feedback.cache_key_for_video(self.video()), namespace=App.version,
            cache_class=layer_cache.KeyValueCache)

    def delete(self):
        db.delete(self)
        self.clear_cache_for_video()

    def put(self):
        db.Model.put(self)
        self.clear_cache_for_video()

    def set_author(self, user_data):
        self.author = user_data.user
        self.author_nickname = user_data.nickname
        self.author_user_id = user_data.user_id

    def authored_by(self, user_data):
        return user_data and self.author == user_data.user

    def is_visible_to_public(self):
        return (not self.deleted and not self.is_hidden_by_flags)

    def is_visible_to(self, user_data):
        """ Returns true if this post should be visible to user_data.
        If user_data is empty, true only if the post should be visible to the general public.
        If someone's post has been deleted or flagged, it's only visible to the original author and developers.
        """
        return self.is_visible_to_public() or self.authored_by(user_data) or (user_data and user_data.developer)

    def appears_as_deleted_to(self, user_data):
        """ Returns true if the post should appear as deleted to user_data.
        This should only be true for posts that are deleted and being viewed by developers.
        """
        return user_data and (user_data.developer or user_data.moderator) and not self.is_visible_to_public()

    @property
    def sum_votes_incremented(self):
        # Always add an extra vote when displaying vote counts to convey the author's implicit "vote"
        # and make the site a little more positive.
        return self.sum_votes + 1

    def is_type(self, type):
        return type in self.types

    def question_key(self):
        if self.targets:
            return self.targets[-1] # last target is always the question
        return None

    def question(self):
        return db.get(self.question_key())

    def children_keys(self):
        keys = db.Query(Feedback, keys_only=True)
        keys.filter("targets = ", self.key())
        return keys

    def video_key(self):
        if self.targets:
            return self.targets[0]
        return None

    def video(self):
        video_key = self.video_key()
        if video_key:
            video = db.get(video_key)
            if video and video.has_topic():
                return video
        return None

    def add_vote_by(self, vote_type, user_data):
        FeedbackVote.add_vote(self, vote_type, user_data)
        self.update_votes_and_score()

    def update_votes_and_score(self):
        self.recalculate_votes()
        self.recalculate_score()
        self.put()

        if self.is_type(FeedbackType.Answer):
            question = self.question()
            if question:
                question.recalculate_score()
                question.put()

    def recalculate_votes(self):
        self.sum_votes = FeedbackVote.count_votes(self)

    def recalculate_score(self):
        score = float(self.sum_votes)

        if self.is_type(FeedbackType.Question):
            for answer in db.get(self.children_keys().fetch(1000)):
                score += 0.5 * float(answer.sum_votes)

        self.inner_score = float(score)

    def add_flag_by(self, flag_type, user_data):
        if user_data.key_email in self.flagged_by:
            return False

        self.flags.append(flag_type)
        self.flagged_by.append(user_data.key_email)
        self.recalculate_flagged()
        return True

    def clear_flags(self):
        self.flags = []
        self.flagged_by = []
        self.recalculate_flagged()

    def recalculate_flagged(self):
        self.is_flagged = len(self.flags or []) > 0
        self.is_hidden_by_flags = len(self.flags or []) >= FeedbackFlag.HIDE_LIMIT

    def get_author_user_id(self):
        if self.author_user_id is not None:
            return self.author_user_id
        else:
            user_data = models.UserData.get_from_user(self.author)
            if user_data is not None:
                return user_data.user_id
            else:
                return ''

    @staticmethod
    def get_all_questions_by_author(user_id):
        """ Get all questions asked by specified user
        """
        query = Feedback.all()

        # STOPSHIP(marcia): Backfill feedback with author user id
        query.filter('author_user_id =', user_id)

        return [q for q in query if q.is_type(FeedbackType.Question)]

class FeedbackNotification(db.Model):
    """ A FeedbackNotification entity is created for each answer to a
    question, unless the question and answer authors are the same user
    """
    # The answer that provoked a notification
    feedback = db.ReferenceProperty(Feedback)

    # The question author and recipient of the notification
    user = db.UserProperty()

    @staticmethod
    def clear_for_user_data(recipient_user_data):
        """ Delete the FeedbackNotifications for the specified recipient
        """
        notifications = FeedbackNotification.gql(
                "WHERE user = :1", recipient_user_data.user)

        if notifications.count():
            db.delete(notifications)
            recipient_user_data.count_feedback_notification = 0
            recipient_user_data.put()


class FeedbackVote(db.Model):
    DOWN = -1
    ABSTAIN = 0
    UP = 1

    # Feedback reference stored in parent property
    video = db.ReferenceProperty()
    user = db.UserProperty()
    vote_type = db.IntegerProperty(default=0)

    @staticmethod
    def add_vote(feedback, vote_type, user_data):
        if not feedback or not user_data:
            return

        vote = FeedbackVote.get_or_insert(
                key_name = "vote_by_%s" % user_data.key_email,
                parent = feedback,
                video = feedback.video_key(),
                user = user_data.user,
                vote_type = vote_type)

        if vote and vote.vote_type != vote_type:
            # If vote already existed and user has changed vote, update
            vote.vote_type = vote_type
            vote.put()

    @staticmethod
    @request_cache.cache_with_key_fxn(lambda user_data, video: "voting_dict_for_%s" % video.key())
    def get_dict_for_user_data_and_video(user_data, video):

        if not user_data:
            return {}

        query = FeedbackVote.all()
        query.filter("user =", user_data.user)
        query.filter("video =", video)
        votes = query.fetch(1000)

        dict = {}
        for vote in votes:
            dict[vote.parent_key()] = vote

        return dict

    @staticmethod
    def count_votes(feedback):
        if not feedback:
            return 0

        query = FeedbackVote.all()
        query.ancestor(feedback)
        votes = query.fetch(100000)

        count_up = len(filter(lambda vote: vote.is_up(), votes))
        count_down = len(filter(lambda vote: vote.is_down(), votes))

        return count_up - count_down

    def is_up(self):
        return self.vote_type == FeedbackVote.UP

    def is_down(self):
        return self.vote_type == FeedbackVote.DOWN
