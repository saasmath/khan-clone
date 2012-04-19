import os

from google.appengine.api import users
from google.appengine.ext import db

from app import App
import app
import user_util
import util
import util_discussion
import request_handler
import user_models
import discussion_models
import voting


def get_questions_data(user_data):
    """ Get data associated with a user's questions and unread answers
    """
    dict_meta_questions = {}

    # Get questions asked by user
    questions = discussion_models.Feedback.get_all_questions_by_author(user_data.user_id)
    for question in questions:
        qa_expand_key = str(question.key())
        meta_question = MetaQuestion.from_question(question, user_data)
        if meta_question:
            dict_meta_questions[qa_expand_key] = meta_question

    # Get unread answers to the above questions
    unread_answers = feedback_answers_for_user_data(user_data)
    for answer in unread_answers:
        question_key = str(answer.question_key())
        if question_key in dict_meta_questions:
            meta_question = dict_meta_questions[question_key]
            meta_question.mark_has_unread()

    return dict_meta_questions.values()

class MetaQuestion(object):
    """ Data associated with a user's question, including the target video
    and notifications count, or None if the associated video no longer exists
    """
    @staticmethod
    def from_question(question, viewer_user_data):
        """ Construct a MetaQuestion from a Feedback entity """
        video = question.video()
        if not video:
            return None

        meta = MetaQuestion()
        meta.video = video

        # qa_expand_key is later used as a url parameter on the video page
        # to expand the question and its answers
        meta.qa_expand_key = str(question.key())
        meta.content = question.content

        meta.set_answer_data(question, viewer_user_data)

        return meta

    def mark_has_unread(self):
        self.has_unread = True

    def set_answer_data(self, question, viewer_user_data):
        """ Set answerer count and last date as seen by the specified viewer
        """
        query = util_discussion.feedback_query(question.key())
        self.answerer_count = 0
        self.last_date = question.date

        # We assume all answers have been read until we see a notification
        self.has_unread = False

        if query.count():
            viewable_answers = [answer for answer in query if
                    not answer.appears_as_deleted_to(viewer_user_data)]

            answerer_user_ids = set(answer.author_user_id for answer
                    in viewable_answers)

            self.answerer_count = len(answerer_user_ids)
            self.last_date = max([answer.date for answer in viewable_answers])


class VideoFeedbackNotificationFeed(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):

        user_data = self.request_user_data("email")

        max_entries = 100
        answers = feedback_answers_for_user_data(user_data)
        answers = sorted(answers, key=lambda answer: answer.date)

        context = {
                    "answers": answers,
                    "count": len(answers)
                  }

        self.response.headers['Content-Type'] = 'text/xml'
        self.render_jinja2_template('discussion/video_feedback_notification_feed.xml', context)

def feedback_answers_for_user_data(user_data):
    feedbacks = []

    if not user_data:
        return feedbacks

    notifications = discussion_models.FeedbackNotification.gql("WHERE user = :1", user_data.user)

    for notification in notifications:

        feedback = None

        try:
            feedback = notification.feedback
        except db.ReferencePropertyResolveError:
            pass

        if not feedback or not feedback.video() or not feedback.is_visible_to_public() or not feedback.is_type(discussion_models.FeedbackType.Answer):
            # If we ever run into notification for a deleted or non-FeedbackType.Answer piece of feedback,
            # go ahead and clear the notification so we keep the DB clean.
            db.delete(notification)
            continue

        feedbacks.append(feedback)

    return feedbacks

# Send a notification to the author of this question, letting
# them know that a new answer is available.
def new_answer_for_video_question(video, question, answer):

    if not question or not question.author:
        return

    # Don't notify if user answering own question
    if question.author == answer.author:
        return

    user_data = user_models.UserData.get_from_user(question.author)
    if not user_data:
        return

    notification = discussion_models.FeedbackNotification()
    notification.user = question.author
    notification.feedback = answer
    notification.put()

    user_data.mark_feedback_notification_count_as_stale()


def clear_notification_for_question(question_key, user_data=None):
    """Clear a notification, if it exists, for specified question and user.
    
    Returns:
        0 in case any of any missing data, otherwise the notification count
        for user_data after having potentially cleared a notification.
    """
    if not question_key:
        return 0

    if not user_data:
        user_data = user_models.UserData.current()
        if not user_data:
            return 0

    question = discussion_models.Feedback.get(question_key)

    if not question:
        return 0

    count = user_data.feedback_notification_count()
    should_recalculate_count = False

    answer_keys = question.children_keys()
    for answer_key in answer_keys:
        notification = discussion_models.FeedbackNotification.gql(
            "WHERE user = :1 AND feedback = :2", user_data.user, answer_key)

        if notification.count():
            should_recalculate_count = True
            db.delete(notification)

    if should_recalculate_count:
        user_data.mark_feedback_notification_count_as_stale()
        # We choose not to call user_data.feedback_notification_count()
        # right away because the FeedbackNotification indices may be stale,
        # and we want to show the user the right # when clicking through
        # an expando video-question link.
        if count > 0:
            count = count - 1

    return count
