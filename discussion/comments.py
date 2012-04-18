from google.appengine.ext import db

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import user_models
import discussion_models
import util_discussion
import user_util
import util
import request_handler
import voting
from phantom_users.phantom_util import disallow_phantoms

class PageComments(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        page = 0
        try:
            page = int(self.request.get("page"))
        except:
            pass

        video_key = self.request.get("video_key")
        sort_order = self.request_int("sort_order", default=voting.VotingSortOrder.HighestPointsFirst)
        video = db.get(video_key)

        if video:
            comments_hidden = self.request_bool("comments_hidden", default=True)
            template_values = video_comments_context(video, page, comments_hidden, sort_order)

            html = self.render_jinja2_template_to_string("discussion/video_comments_content.html", template_values)
            self.render_json({"html": html, "page": page})

class AddComment(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.open_access
    def post(self):
        user_data = user_models.UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        if not util_discussion.is_honeypot_empty(self.request):
            # Honeypot caught a spammer (in case this is ever public or spammers
            # have google accounts)!
            return

        comment_text = self.request.get("comment_text")
        comments_hidden = self.request.get("comments_hidden")
        video_key = self.request.get("video_key")
        video = db.get(video_key)

        if comment_text and video:
            if len(comment_text) > 300:
                comment_text = comment_text[0:300] # max comment length, also limited by client

            comment = discussion_models.Feedback(parent=user_data)
            comment.set_author(user_data)
            comment.content = comment_text
            comment.targets = [video.key()]
            comment.types = [discussion_models.FeedbackType.Comment]

            if user_data.discussion_banned:
                # Hellbanned users' posts are automatically hidden
                comment.deleted = True

            comment.put()

        self.redirect("/discussion/pagecomments?video_key=%s&page=0&comments_hidden=%s&sort_order=%s" % 
                (video_key, comments_hidden, voting.VotingSortOrder.NewestFirst))

def video_comments_context(video, page=0, comments_hidden=True, sort_order=voting.VotingSortOrder.HighestPointsFirst):

    user_data = user_models.UserData.current()

    if page > 0:
        comments_hidden = False # Never hide questions if specifying specific page
    else:
        page = 1

    limit_per_page = 10
    limit_initially_visible = 2 if comments_hidden else limit_per_page

    comments = util_discussion.get_feedback_by_type_for_video(video, discussion_models.FeedbackType.Comment, user_data)
    comments = voting.VotingSortOrder.sort(comments, sort_order=sort_order)

    count_total = len(comments)
    comments = comments[((page - 1) * limit_per_page):(page * limit_per_page)]

    dict_votes = discussion_models.FeedbackVote.get_dict_for_user_data_and_video(user_data, video)
    for comment in comments:
        voting.add_vote_expando_properties(comment, dict_votes)

    count_page = len(comments)
    pages_total = max(1, ((count_total - 1) / limit_per_page) + 1)
    return {
            "is_mod": user_util.is_current_user_moderator(),
            "video": video,
            "comments": comments,
            "count_total": count_total,
            "comments_hidden": count_page > limit_initially_visible,
            "limit_initially_visible": limit_initially_visible,
            "pages": range(1, pages_total + 1),
            "pages_total": pages_total,
            "prev_page_1_based": page - 1,
            "current_page_1_based": page,
            "next_page_1_based": page + 1,
            "show_page_controls": pages_total > 1,
           }
