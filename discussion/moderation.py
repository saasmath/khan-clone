from google.appengine.ext import db
from google.appengine.api import users

import request_handler
import models
import models_discussion
from user_util import admin_only, moderator_only

class RedirectToModPanel(request_handler.RequestHandler):
    def get(self):
        self.redirect("/discussion/mod")

class ModPanel(request_handler.RequestHandler):

    @moderator_only
    def get(self):
        self.render_jinja2_template('discussion/mod/mod.html', { "selected_id": "panel" })

class ModeratorList(request_handler.RequestHandler):

    # Must be an admin to change moderators
    @admin_only
    def get(self):
        mods = models.UserData.gql("WHERE moderator = :1", True)
        self.render_jinja2_template('discussion/mod/moderatorlist.html', {
            "mods" : mods,
            "selected_id": "moderatorlist",
        })

    @admin_only
    def post(self):
        user_data = self.request_user_data("user")

        if user_data:
            user_data.moderator = self.request_bool("mod")
            db.put(user_data)

        self.redirect("/discussion/mod/moderatorlist")

class FlaggedFeedback(request_handler.RequestHandler):

    @moderator_only
    def get(self):

        # Show all non-deleted feedback flagged for moderator attention
        feedback_query = models_discussion.Feedback.all().filter("is_flagged = ", True).filter("deleted = ", False)

        feedback_count = feedback_query.count()
        feedbacks = feedback_query.fetch(50)

        template_content = {
                "feedbacks": feedbacks, 
                "feedback_count": feedback_count,
                "has_more": len(feedbacks) < feedback_count,
                "feedback_type_question": models_discussion.FeedbackType.Question,
                "feedback_type_comment": models_discussion.FeedbackType.Comment,
                "selected_id": "flaggedfeedback",
                }

        self.render_jinja2_template("discussion/mod/flaggedfeedback.html", template_content)

