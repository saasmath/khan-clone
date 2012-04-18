try:
    import unittest2 as unittest
except ImportError:
    import unittest

from third_party.agar.test import BaseTest

# TODO(marcia): Not sure why user_models has to come first
import user_models
import discussion_models
import notification
import video_models

class FeedbackNotificationTest(BaseTest):
    def make_video(self):
        video = video_models.Video()
        video.topic_string_keys = "irrelevant, but can't be None"
        video.put()
        return video

    def make_question(self, content, video, user_data):
        return discussion_models.Feedback.insert_question_for(content,
                                                              video,
                                                              user_data)
    def make_user_data(self, email):
        return user_models.UserData.insert_for(email, email)

    def make_answer(self, content, question, user_data):
        answer = discussion_models.Feedback.insert_answer_for(content,
                                                              question,
                                                              user_data)
        notification.new_answer_for_video_question(question.video(),
                                                   question,
                                                   answer)

        return answer

    def test_increase_notification_count_with_new_answer(self):
        video = self.make_video()
        asker = self.make_user_data('weasley@gmail.com')
        answerer = self.make_user_data('hermione@gmail.com')

        question = self.make_question("Where did Harry go?",
                                      video,
                                      asker)
        self.make_answer("He went to the loo.",
                         question,
                         answerer)

        self.assertEqual(1, asker.feedback_notification_count())

    def test_reset_notification_count_upon_read(self):
        video = self.make_video()
        asker = self.make_user_data('weasley@gmail.com')
        answerer = self.make_user_data('hermione@gmail.com')

        question = self.make_question("Where did Harry go?",
                                      video,
                                      asker)

        self.make_answer("He went to the loo.",
                         question,
                         answerer)

        notification.clear_notification_for_question(question.key(), asker)

        self.assertEqual(0, asker.feedback_notification_count())

    def test_have_one_notification_for_answers_on_same_question(self):
        video = self.make_video()
        asker = self.make_user_data('weasley@gmail.com')
        answerer = self.make_user_data('hermione@gmail.com')
        other_answerer = self.make_user_data('harry@gmail.com')

        question = self.make_question("Where did Harry go?",
                                      video,
                                      asker)
        self.make_answer("He went to the loo.",
                         question,
                         answerer)
        self.make_answer("No, I'm right here!",
                         question,
                         other_answerer)

        self.assertEqual(1, asker.feedback_notification_count())

    def test_no_notification_for_answering_own_question(self):
        video = self.make_video()
        asker = self.make_user_data('weasley@gmail.com')
        question = self.make_question("Where did Harry go?",
                                      video,
                                      asker)
        self.make_answer("Oh, I know where he went.",
                         question,
                         asker)
        self.assertEqual(0, asker.feedback_notification_count())

    def test_no_notification_for_question_changed_to_comment(self):
        video = self.make_video()
        asker = self.make_user_data('weasley@gmail.com')
        answerer = self.make_user_data('hermione@gmail.com')

        question = self.make_question("Where did Harry go?",
                                      video,
                                      asker)
        self.make_answer("He went to the loo.",
                         question,
                         answerer)

        question.change_type(discussion_models.FeedbackType.Comment)
        self.assertEqual(0, asker.feedback_notification_count())

    def test_regain_notification_for_question_changed_to_comment_and_back(self):
        video = self.make_video()
        asker = self.make_user_data('weasley@gmail.com')
        answerer = self.make_user_data('hermione@gmail.com')

        question = self.make_question("Where did Harry go?",
                                      video,
                                      asker)
        self.make_answer("He went to the loo.",
                         question,
                         answerer)

        question.change_type(discussion_models.FeedbackType.Comment)
        question.change_type(discussion_models.FeedbackType.Question)
        self.assertEqual(1, asker.feedback_notification_count())
