from google.appengine.ext import db
from mapreduce import control
from mapreduce import operation as op

import user_models
import discussion_models
import notification
import util_discussion
import user_util
import util
import request_handler
import voting
from phantom_users.phantom_util import disallow_phantoms
from rate_limiter import FlagRateLimiter
from badges.discussion_badges import FirstFlagBadge

def feedback_flag_update_map(feedback):
    feedback.recalculate_flagged()
    yield op.db.Put(feedback)

class StartNewFlagUpdateMapReduce(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        mapreduce_id = control.start_map(
                name = "FeedbackFlagUpdate",
                handler_spec = "discussion.qa.feedback_flag_update_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "discussion.discussion_models.Feedback"},
                shard_count = 64,
                queue_name = "backfill-mapreduce-queue",
                )
        self.response.out.write("OK: " + str(mapreduce_id))

class ExpandQuestion(request_handler.RequestHandler):
    @user_util.open_access
    def post(self):
        notification.clear_notification_for_question(self.request.get("qa_expand_key"))

class PageQuestions(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        page = 0
        try:
            page = int(self.request.get("page"))
        except:
            pass

        video_key = self.request.get("video_key")
        qa_expand_key = self.request_string("qa_expand_key")
        sort = self.request_int("sort", default=-1)
        video = db.get(video_key)

        user_data = user_models.UserData.current()
        count = user_data.feedback_notification_count() if user_data else 0

        if qa_expand_key:
            # Clear unread answer notification for expanded question
            count = notification.clear_notification_for_question(qa_expand_key)

        if video:
            template_values = video_qa_context(user_data, video, page, qa_expand_key, sort)
            html = self.render_jinja2_template_to_string("discussion/video_qa_content.html", template_values)
            self.render_json({
                "html": html,
                "page": page,
                "qa_expand_key": qa_expand_key,
                "count_notifications": count,
            })

        return

class AddAnswer(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.open_access
    def post(self):

        user_data = user_models.UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        if not util_discussion.is_post_allowed(user_data, self.request):
            return

        answer_text = self.request.get("answer_text")
        video_key = self.request.get("video_key")
        question_key = self.request.get("question_key")

        video = db.get(video_key)
        question = db.get(question_key)

        if answer_text and video and question:
            answer = discussion_models.Feedback.insert_answer_for(answer_text,
                                                                  question,
                                                                  user_data)

            if user_data.discussion_banned:
                # Hellbanned users' posts are automatically hidden
                answer.deleted = True
                answer.put()

            if not answer.deleted:
                notification.new_answer_for_video_question(video, question, answer)

        self.redirect("/discussion/answers?question_key=%s" % question_key)

class Answers(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        user_data = user_models.UserData.current()
        question_key = self.request.get("question_key")
        question = db.get(question_key)

        if question:
            video = question.video()
            dict_votes = discussion_models.FeedbackVote.get_dict_for_user_data_and_video(user_data, video)

            answers = discussion_models.Feedback.gql("WHERE types = :1 AND targets = :2", discussion_models.FeedbackType.Answer, question.key()).fetch(1000)
            answers = filter(lambda answer: answer.is_visible_to(user_data), answers)
            answers = voting.VotingSortOrder.sort(answers)

            for answer in answers:
                voting.add_vote_expando_properties(answer, dict_votes)

            template_values = {
                "answers": answers,
                "is_mod": user_util.is_current_user_moderator()
            }

            html = self.render_jinja2_template_to_string('discussion/question_answers_only.html', template_values)
            self.render_json({"html": html})

        return

class AddQuestion(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.open_access
    def post(self):

        user_data = user_models.UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        if not util_discussion.is_post_allowed(user_data, self.request):
            return

        text = self.request.get("question_text")
        video_key = self.request.get("video_key")
        video = db.get(video_key)
        question_key = ""

        if text and video:
            if len(text) > 500:
                text = text[0:500] # max question length, also limited by client

            question = discussion_models.Feedback.insert_question_for(text,
                                                                      video,
                                                                      user_data)

            if user_data.discussion_banned:
                # Hellbanned users' posts are automatically hidden
                question.deleted = True
                question.put()

            question_key = question.key()

        self.redirect("/discussion/pagequestions?video_key=%s&qa_expand_key=%s" % 
                (video_key, question_key))

class EditEntity(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.open_access
    def post(self):
        user_data = user_models.UserData.current()
        if not user_data:
            return

        key = self.request.get("entity_key")
        text = self.request.get("question_text") or self.request.get("answer_text")

        if key and text:
            feedback = db.get(key)
            if feedback:
                if feedback.authored_by(user_data) or user_util.is_current_user_moderator():

                    feedback.content = text
                    feedback.put()

                    # Redirect to appropriate list of entities depending on type of 
                    # feedback entity being edited.
                    if feedback.is_type(discussion_models.FeedbackType.Question):

                        page = self.request.get("page")
                        video = feedback.video()
                        self.redirect("/discussion/pagequestions?video_key=%s&page=%s&qa_expand_key=%s" % 
                                        (video.key(), page, feedback.key()))

                    elif feedback.is_type(discussion_models.FeedbackType.Answer):

                        question = feedback.question()
                        self.redirect("/discussion/answers?question_key=%s" % question.key())

class FlagEntity(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.open_access
    def post(self):
        # You have to at least be logged in to flag
        user_data = user_models.UserData.current()
        if not user_data:
            return

        limiter = FlagRateLimiter(user_data)
        if not limiter.increment():
            self.render_json({"error": limiter.denied_desc()})
            return

        key = self.request_string("entity_key", default="")
        flag = self.request_string("flag", default="")
        if key and discussion_models.FeedbackFlag.is_valid(flag):
            entity = db.get(key)
            if entity and entity.add_flag_by(flag, user_data):
                entity.put()

                if not FirstFlagBadge().is_already_owned_by(user_data):
                    FirstFlagBadge().award_to(user_data)
                    user_data.put()

class ClearFlags(request_handler.RequestHandler):
    @user_util.moderator_only
    def post(self):
        key = self.request.get("entity_key")
        if key:
            entity = db.get(key)
            if entity:
                entity.clear_flags()
                entity.put()

        self.redirect("/discussion/flaggedfeedback")

class ChangeEntityType(request_handler.RequestHandler):
    @user_util.moderator_only
    def post(self):
        # Must be a moderator to change types of anything
        if not user_util.is_current_user_moderator():
            return

        key = self.request.get("entity_key")
        target_type = self.request.get("target_type")

        if key:
            entity = db.get(key)
            if entity:
                clear_flags = self.request_bool("clear_flags", default=False)
                entity.change_type(target_type, clear_flags)

        self.redirect("/discussion/flaggedfeedback")

class DeleteEntity(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.manual_access_checking
    def post(self):
        user_data = user_models.UserData.current()
        if not user_data:
            return

        key = self.request.get("entity_key")
        if key:
            entity = db.get(key)
            if entity:
                # Must be a moderator or author of entity to delete
                if entity.authored_by(user_data):
                    # Entity authors can completely delete their posts.
                    # Posts that are flagged as deleted by moderators won't show up
                    # as deleted to authors, so we just completely delete in this special case.
                    entity.delete()
                elif user_util.is_current_user_moderator():
                    entity.deleted = True
                    entity.put()

        self.redirect("/discussion/flaggedfeedback")

def video_qa_context(user_data, video, page=0, qa_expand_key=None, sort_override=-1):
    limit_per_page = 5

    if page <= 0:
        page = 1

    sort_order = voting.VotingSortOrder.HighestPointsFirst
    if user_data:
        sort_order = user_data.question_sort_order
    if sort_override >= 0:
        sort_order = sort_override

    questions = util_discussion.get_feedback_by_type_for_video(video, discussion_models.FeedbackType.Question, user_data)
    questions = voting.VotingSortOrder.sort(questions, sort_order=sort_order)

    if qa_expand_key:
        # If we're showing an initially expanded question,
        # make sure we're on the correct page
        question = discussion_models.Feedback.get(qa_expand_key)
        if question:
            count_preceding = 0
            for question_test in questions:
                if question_test.key() == question.key():
                    break
                count_preceding += 1
            page = 1 + (count_preceding / limit_per_page)

    answers = util_discussion.get_feedback_by_type_for_video(video, discussion_models.FeedbackType.Answer, user_data)
    answers.reverse() # Answers are initially in date descending -- we want ascending before the points sort
    answers = voting.VotingSortOrder.sort(answers)

    dict_votes = discussion_models.FeedbackVote.get_dict_for_user_data_and_video(user_data, video)

    count_total = len(questions)
    questions = questions[((page - 1) * limit_per_page):(page * limit_per_page)]

    dict_questions = {}
    # Store each question in this page in a dict for answer population
    for question in questions:
        voting.add_vote_expando_properties(question, dict_votes)
        dict_questions[question.key()] = question

    # Just grab all answers for this video and cache in page's questions
    for answer in answers:
        # Grab the key only for each answer, don't run a full gql query on the ReferenceProperty
        question_key = answer.question_key()
        if (dict_questions.has_key(question_key)):
            question = dict_questions[question_key]
            voting.add_vote_expando_properties(answer, dict_votes)
            question.children_cache.append(answer)

    count_page = len(questions)
    pages_total = max(1, ((count_total - 1) / limit_per_page) + 1)
    return {
            "is_mod": user_util.is_current_user_moderator(),
            "video": video,
            "questions": questions,
            "count_total": count_total,
            "pages": range(1, pages_total + 1),
            "pages_total": pages_total,
            "prev_page_1_based": page - 1,
            "current_page_1_based": page,
            "next_page_1_based": page + 1,
            "show_page_controls": pages_total > 1,
            "qa_expand_key": qa_expand_key,
            "sort_order": sort_order,
           }

def add_template_values(dict, request):
    dict["comments_page"] = int(request.get("comments_page")) if request.get("comments_page") else 0
    dict["qa_page"] = int(request.get("qa_page")) if request.get("qa_page") else 0
    dict["qa_expand_key"] = request.get("qa_expand_key")
    dict["sort"] = int(request.get("sort")) if request.get("sort") else -1

    return dict
