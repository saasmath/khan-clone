from operator import itemgetter
from google.appengine.ext import db

import api.auth.xsrf
import request_handler
import user_models
import discussion_models
from badges.discussion_badges import ModeratorBadge
import user_util


class ModPanel(request_handler.RequestHandler):
    @user_util.moderator_required
    def get(self):
        template_values = {
            'selected_id': 'panel',
        }
        self.render_jinja2_template('discussion/mod/mod.html',
                                    template_values)


class ModeratorList(request_handler.RequestHandler):
    # Must be an admin to change moderators
    @user_util.admin_required
    def get(self):
        mods = user_models.UserData.gql('WHERE moderator = :1', True)
        template_values = {
            'mods': mods,
            'selected_id': 'moderatorlist',
        }
        self.render_jinja2_template('discussion/mod/moderatorlist.html',
                                    template_values)

    @user_util.admin_required
    def post(self):
        user_data = self.request_user_data('user')

        if user_data:
            user_data.moderator = self.request_bool('mod')

            if user_data.moderator:
                if not ModeratorBadge().is_already_owned_by(user_data):
                    ModeratorBadge().award_to(user_data)

            db.put(user_data)

        self.redirect('/discussion/mod/moderatorlist')


class FlaggedFeedback(request_handler.RequestHandler):
    @user_util.moderator_required
    def get(self):
        # Show all non-deleted feedback flagged for moderator attention
        feedback_query = discussion_models.Feedback.all()
        feedback_query = feedback_query.filter('is_flagged = ', True)
        feedback_query = feedback_query.filter('deleted = ', False)

        feedback_count = feedback_query.count()

        # Grab a bunch of flagged pieces of feedback and point moderators at
        # the 50 w/ lowest votes first.
        # ...can easily do this w/ an order on the above query and a new index,
        # but avoiding the index for now since it's only marginally helpful.
        feedbacks = feedback_query.fetch(250)
        feedbacks = sorted(feedbacks, key=lambda feedback: feedback.sum_votes)

        author_histogram = {}
        for feedback in feedbacks:
            count = author_histogram.setdefault(feedback.author, 0) + 1
            author_histogram[feedback.author] = count
        author_count_tuples = sorted(author_histogram.items(),
                                     key=itemgetter(1),
                                     reverse=True)

        feedbacks = feedbacks[:50]

        feedback_type_question = discussion_models.FeedbackType.Question
        feedback_type_comment = discussion_models.FeedbackType.Comment
        template_values = {
                'feedbacks': feedbacks,
                'feedback_count': feedback_count,
                'has_more': len(feedbacks) < feedback_count,
                'feedback_type_question': feedback_type_question,
                'feedback_type_comment': feedback_type_comment,
                'selected_id': 'flaggedfeedback',
                'author_count_tuples': author_count_tuples,
                }

        self.render_jinja2_template('discussion/mod/flaggedfeedback.html',
                                    template_values)


class BannedList(request_handler.RequestHandler):
    @user_util.moderator_required
    def get(self):
        banned_user_data_list = user_models.UserData.gql(
                'WHERE discussion_banned = :1', True)
        template_values = {
            'banned_user_data_list': banned_user_data_list,
            'selected_id': 'bannedlist',
        }
        self.render_jinja2_template('discussion/mod/bannedlist.html',
                                    template_values)

    @user_util.moderator_required
    def post(self):
        user_data = self.request_user_data('user')

        if user_data:
            user_data.discussion_banned = self.request_bool('banned')
            db.put(user_data)

            if user_data.discussion_banned:
                # Delete all old posts by hellbanned user
                query = discussion_models.Feedback.all()
                query.ancestor(user_data)
                for feedback in query:
                    if not feedback.deleted:
                        feedback.deleted = True
                        feedback.put()

        self.redirect('/discussion/mod/bannedlist')
