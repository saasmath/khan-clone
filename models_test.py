try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import patch
from agar.test.base_test import BaseTest
from google.appengine.ext import db

# TODO(benkomalo): move away form using testutil.GAEModelTestCase to agar.test.BaseTest
import models
import custom_exceptions
import coaches
import phantom_users.phantom_util
import testutil
from testutil import testsize


class UserDataCoachTest(BaseTest):

    def make_user(self, email):
        u = models.UserData.insert_for(email, email)
        u.put()
        return u

    def make_user_json(self, user, is_coaching):
        return {
            'email': user.key_email,
            'isCoachingLoggedInUser': is_coaching,
        }

    def test_add_a_coach(self):
        student = self.make_user('student@gmail.com')
        coach = self.make_user('coach@gmail.com')

        coaches_json = [self.make_user_json(coach, True)]
        coaches.update_coaches(student, coaches_json)

        self.assertEqual(1, len(student.coaches))
        self.assertTrue(student.is_visible_to(coach))
        self.assertTrue(coach.has_students())

    def test_add_multiple_coaches(self):
        bella = self.make_user('bella@gmail.com')
        jacob = self.make_user('jacob@gmail.com')
        edward = self.make_user('edward@gmail.com')

        coaches_json = [self.make_user_json(coach, True) for coach in
                [jacob, edward]]
        coaches.update_coaches(bella, coaches_json)

        self.assertEqual(2, len(bella.coaches))

        self.assertTrue(bella.is_visible_to(jacob))
        self.assertTrue(jacob.has_students())

        self.assertTrue(bella.is_visible_to(edward))
        self.assertTrue(edward.has_students())

    def test_remove_coach(self):
        bella = self.make_user('bella@gmail.com')
        jacob = self.make_user('jacob@gmail.com')

        jacob_json = [self.make_user_json(jacob, True)]
        coaches.update_coaches(bella, jacob_json)
        coaches.update_coaches(bella, [])

        self.assertEqual(0, len(bella.coaches))
        self.assertFalse(bella.is_visible_to(jacob))
        self.assertFalse(jacob.has_students())

    def test_return_no_requester_emails_on_update_coaches_when_coaching_logged_in_user(self):
        bella = self.make_user('bella@gmail.com')
        jacob = self.make_user('jacob@gmail.com')

        jacob_json = [self.make_user_json(jacob, True)]
        requester_emails = coaches.update_coaches(bella, jacob_json)

        self.assertEqual([], requester_emails)

    def test_return_requester_email_on_update_coaches_when_not_coaching_logged_in_user(self):
        bella = self.make_user('bella@gmail.com')
        jacob = self.make_user('jacob@gmail.com')

        jacob_json = [self.make_user_json(jacob, False)]
        requester_emails = coaches.update_coaches(bella, jacob_json)

        self.assertEqual([jacob.key_email], requester_emails)

    def test_raises_exception_on_add_nonexistent_coach(self):
        bella = self.make_user('bella@gmail.com')
        coaches_json = [{
            'email': 'legolas@gmail.com',
            'isCoachingLoggedInUser': True,
        }]
        self.assertRaises(custom_exceptions.InvalidEmailException,
            coaches.update_coaches,
            bella,
            coaches_json)

    def test_noop_on_update_requests_with_email(self):
        bella = self.make_user('bella@gmail.com')
        jacob = self.make_user('jacob@gmail.com')

        models.CoachRequest.get_or_insert_for(jacob, bella)

        coaches.update_requests(bella, [jacob.key_email])

        requests_for_bella = models.CoachRequest.get_for_student(bella).fetch(1000)
        self.assertEqual(1, len(requests_for_bella))

        requests_by_jacob = models.CoachRequest.get_for_coach(jacob).fetch(1000)
        self.assertEqual(1, len(requests_by_jacob))

    def test_clear_request_on_update_requests_with_no_email(self):
        bella = self.make_user('bella@gmail.com')
        edward = self.make_user('edward@gmail.com')
        models.CoachRequest.get_or_insert_for(edward, bella)

        coaches.update_requests(bella, [])

        requests_for_bella = models.CoachRequest.get_for_student(bella).fetch(1000)
        self.assertEqual(0, len(requests_for_bella))

        requests_by_edward = models.CoachRequest.get_for_coach(edward).fetch(1000)
        self.assertEqual(0, len(requests_by_edward))

    def test_noop_on_update_when_not_coaching_logged_in_user(self):
        # Bella + Edward's daughter,
        # (Spoiler Alert!) who Jacob falls in love with in Book 4
        renesmee = self.make_user('renesmee@gmail.com')
        jacob = self.make_user('jacob@gmail.com')
        models.CoachRequest.get_or_insert_for(jacob, renesmee)
        requests_for_renesmee = models.CoachRequest.get_for_student(renesmee).fetch(1000)
        self.assertEqual(1, len(requests_for_renesmee))

        coaches_json = [self.make_user_json(jacob, False)]
        coaches.update_coaches_and_requests(renesmee, coaches_json)

        self.assertFalse(renesmee.is_visible_to(jacob))
        requests_for_renesmee = models.CoachRequest.get_for_student(renesmee).fetch(1000)
        self.assertEqual(1, len(requests_for_renesmee))

    def test_accept_request_on_update_when_coaching_logged_in_user(self):
        renesmee = self.make_user('renesmee@gmail.com')
        jacob = self.make_user('jacob@gmail.com')
        models.CoachRequest.get_or_insert_for(jacob, renesmee)

        coaches_json = [self.make_user_json(jacob, True)]
        coaches.update_coaches_and_requests(renesmee, coaches_json)

        self.assertTrue(renesmee.is_visible_to(jacob))
        requests_for_renesmee = models.CoachRequest.get_for_student(renesmee).fetch(1000)
        self.assertEqual(0, len(requests_for_renesmee))

    def test_ignore_nonexistent_requester_email_on_update_requests(self):
        renesmee = self.make_user('renesmee@gmail.com')
        jacob = self.make_user('jacob@gmail.com')
        models.CoachRequest.get_or_insert_for(jacob, renesmee)

        coaches_json = [{
            'email': 'legolas@gmail.com',
            'isCoachingLoggedInUser': False,
        }]
        coaches.update_requests(renesmee, coaches_json)
        requests_for_renesmee = models.CoachRequest.get_for_student(renesmee).fetch(1000)
        self.assertEqual(0, len(requests_for_renesmee))

class UsernameTest(testutil.GAEModelTestCase):
    def tearDown(self):
        # Clear all usernames just to be safe
        for u in models.UniqueUsername.all():
            u.delete()
        super(UsernameTest, self).tearDown()

    def validate(self, username):
        return models.UniqueUsername.is_valid_username(username)

    def test_user_name_validates_length_requirement(self):
        # This test verifies that the multiple places that verify a username's
        # length are in sync.
        for i in range(10):
            candidate = 'a' * i
            self.assertEquals(
                    not models.UniqueUsername.is_username_too_short(candidate),
                    self.validate(candidate))

    def test_user_name_fuzzy_match(self):
        """ Tests user name search can ignore periods properly. """
        def k(n):
            return models.UniqueUsername.build_key_name(n)

        self.assertEqual(k('mr.pants'), k('mrpants'))
        self.assertEqual(k('mr.pants...'), k('mrpants'))
        self.assertEqual(k('mrpants'), k('mrpants'))
        self.assertEqual(k('MrPants'), k('mrpants'))

    def test_bad_user_name_fails_validation(self):
        self.assertFalse(self.validate(''))
        self.assertFalse(self.validate('a')) # Too short
        self.assertFalse(self.validate('4scoresand7years')) # Must start with letter
        self.assertFalse(self.validate('.dotsarebadtoo'))
        self.assertFalse(self.validate('!nvalid'))
        self.assertFalse(self.validate('B@dCharacters'))
        self.assertFalse(self.validate('I cannot read instructions'))
        self.assertFalse(self.validate(u'h\u0400llojello')) # Cyrillic chars
        self.assertFalse(self.validate('mrpants@khanacademy.org'))

    def test_good_user_name_validates(self):
        self.assertTrue(self.validate('poopybutt'))
        self.assertTrue(self.validate('mrpants'))
        self.assertTrue(self.validate('instructionsareeasy'))
        self.assertTrue(self.validate('coolkid1983'))

    def make_user(self, email):
        u = models.UserData.insert_for(email, email)
        u.put()
        return u

    def test_claiming_username_works(self):
        u1 = self.make_user("bob")
        u2 = self.make_user("robert")

        # Free
        self.assertTrue(u1.claim_username("superbob"))
        self.assertEqual("superbob", u1.username)

        # Now it's taken
        self.assertFalse(u2.claim_username("superbob"))

        # But something completely different should still be good
        self.assertTrue(u2.claim_username("sadbob"))
        self.assertEqual("sadbob", u2.username)

    def test_releasing_usernames(self):
        clock = testutil.MockDatetime()
        u1 = self.make_user("bob")
        u2 = self.make_user("robert")

        # u1 gets "superbob", but changes his mind.
        self.assertTrue(u1.claim_username("superbob", clock))
        self.assertEqual("superbob", u1.username)
        self.assertTrue(u1.claim_username("ultrabob", clock))
        self.assertEqual("ultrabob", u1.username)

        # TOTAL HACK - for some reason without this read (which shouldn't
        # actually have any side effect), the following assert fails because
        # there's no strong consistency ensured on the HRD.
        db.get([u1.key()])
        self.assertEqual(
                u1.user_id,
                models.UserData.get_from_username("ultrabob").user_id)
        self.assertEqual(
                None,
                models.UserData.get_from_username("superbob"))

        # Usernames go into a holding pool, even after they're released
        self.assertFalse(u2.claim_username("superbob", clock))

        # Note that the original owner can't even have it back
        self.assertFalse(u1.claim_username("superbob", clock))

        # Still no good at the border of the holding period
        clock.advance(models.UniqueUsername.HOLDING_PERIOD_DELTA)
        self.assertFalse(u2.claim_username("superbob", clock))

        # OK - now u2 can have it.
        clock.advance_days(1)
        self.assertTrue(u2.claim_username("superbob", clock))
        self.assertEqual("superbob", u2.username)

        db.get([u2.key()])
        self.assertEqual(
                u2.user_id,
                models.UserData.get_from_username("superbob").user_id)

class ProfileSegmentTest(testutil.GAEModelTestCase):
    def to_url(self, user):
        return user.prettified_user_email
    def from_url(self, segment):
        return models.UserData.get_from_url_segment(segment)

    def create_phantom(self):
        user_id = phantom_users.phantom_util._create_phantom_user_id()
        return models.UserData.insert_for(user_id, user_id)

    def test_url_segment_generation(self):
        # Pre-phantom users can't have profile URL's
        prephantom = models.UserData.pre_phantom()
        self.assertTrue(self.from_url(self.to_url(prephantom)) is None)

        # Phantom users can't have profile URL's
        phantom = self.create_phantom()
        self.assertTrue(self.from_url(self.to_url(phantom)) is None)

        # Normal users are cool, though.
        bob = models.UserData.insert_for(
                "http://googleid.khanacademy.org/1234",
                "bob@gmail.com")
        bob.put()
        self.assertEqual(
                self.from_url(self.to_url(bob)).user_id,
                bob.user_id)

        sally = models.UserData.insert_for(
                "http://facebookid.khanacademy.org/1234",
                "http://facebookid.khanacademy.org/1234")
        sally.put()
        self.assertEqual(
                self.from_url(self.to_url(sally)).user_id,
                sally.user_id)

class PromoRecordTest(testutil.GAEModelTestCase):
    # Shorthand
    def r(self, promo_name, user_id):
        return models.PromoRecord.record_promo(promo_name, user_id)

    def test_promo_record(self):
        u1 = "http://facebookid.khanacademy.org/1234"
        u2 = "http://googleid.khanacademy.org/5678"
        p1 = "Public profiles"
        p2 = "Skynet"

        # First time
        self.assertTrue(self.r(p1, u1))
        # Second time and onwards
        for i in range(10):
            self.assertFalse(self.r(p1, u1))

        # Different user
        self.assertTrue(self.r(p1, u2))

        # Different promo
        self.assertTrue(self.r(p2, u1))

class VideoSubtitlesTest(unittest.TestCase):
    def test_get_key_name(self):
        kn = models.VideoSubtitles.get_key_name('en', 'YOUTUBEID')
        self.assertEqual(kn, 'en:YOUTUBEID')

    def test_load_valid_json(self):
        subs = models.VideoSubtitles(json='[{"text":"subtitle"}]')
        json = subs.load_json()
        self.assertIsNotNone(json)
        self.assertEqual([{u'text': u'subtitle'}], json)

    @patch('models.logging.warn')
    def test_log_warning_on_invalid_json(self, warn):
        subs = models.VideoSubtitles(json='invalid json')
        json = subs.load_json()
        self.assertIsNone(json)
        self.assertEqual(warn.call_count, 1, 'logging.warn() not called')

class UserDataCreationTest(testutil.GAEModelTestCase):
    def flush(self, items):
        """ Ensures items are flushed in the HRD. """
        db.get([item.key() for item in items if item])

    def insert_user(self, user_id, email, username=None, password=None):
        return models.UserData.insert_for(user_id, email, username, password)
    
    def test_creation_without_username(self):
        added = [
            self.insert_user("larry", "email1@gmail.com"),
            self.insert_user("curly", "email2@gmail.com"),
            self.insert_user("moe", "email3@gmail.com"),
        ]
        # We don't care about consistency policy issues - we just want proper
        # counts and such.
        self.flush(added)
        self.assertEqual(3, models.UserData.all().count())
        self.assertEqual(set(["larry", "curly", "moe"]),
                         set(user.user_id for user in models.UserData.all()))
        
        # "Re-adding" moe doesn't duplicate.
        self.flush([self.insert_user("moe", "email3@gmail.com")])
        self.assertEqual(3, models.UserData.all().count())

    def test_creation_with_bad_username(self):
        self.assertTrue(self.insert_user("larry", "email1@gmail.com", "!!!!!")
                        is None)
        
    def test_creation_with_existing_username(self):
        self.flush([self.insert_user("larry", "email1@gmail.com", "larry")])
        self.assertEqual(1, models.UserData.all().count())
        self.assertEqual("larry", models.UserData.all()[0].user_id)
        self.assertEqual("larry", models.UserData.all()[0].username)

        self.assertTrue(self.insert_user("larry2", "tooslow@gmail.com", "larry")
                        is None)
        
    @testsize.medium()
    def test_creation_with_password(self):
        self.flush([self.insert_user("larry",
                                     "email1@gmail.com",
                                     "larry",
                                     "Password1")])
        self.assertEqual(1, models.UserData.all().count())
        retrieved = models.UserData.all()[0]
        self.assertEqual("larry", retrieved.user_id)
        self.assertTrue(retrieved.validate_password("Password1"))
        self.assertFalse(retrieved.validate_password("Password2"))


class UserConsumptionTest(testutil.GAEModelTestCase):

    def make_exercise(self, name):
        exercise = models.Exercise(name=name)
        exercise.put()
        return exercise
        
    @testsize.medium()
    def test_user_identity_consumption(self):
        superman = models.UserData.insert_for(
                "superman@gmail.krypt",
                email="superman@gmail.krypt",
                username="superman",
                password="Password1",
                gender="male",
                )

        clark = models.UserData.insert_for(
                "clark@kent.com",
                email="clark@kent.com",
                username=None,
                password=None,
                )

        clark.consume_identity(superman)
        self.assertEqual("superman@gmail.krypt", clark.user_id)
        self.assertEqual("superman@gmail.krypt", clark.email)
        self.assertEqual(clark.key(),
                         models.UserData.get_from_username("superman").key())
        self.assertEqual(clark.key(),
                         models.UserData.get_from_user_id("superman@gmail.krypt").key())
        self.assertTrue(clark.validate_password("Password1"))
        
    def test_user_exercise_preserved_after_consuming(self):
        # A user goes on as a phantom...
        phantom = models.UserData.insert_for("phantom", "phantom")
        exercises = [
                self.make_exercise("Adding 1"),
                self.make_exercise("Multiplication yo"),
                self.make_exercise("All about chickens"),
                ]

        # Does some exercises....
        for e in exercises:
            ue = phantom.get_or_insert_exercise(e)
            ue.total_done = 7
            ue.put()

        # Signs up!
        jimmy = models.UserData.insert_for("justjoinedjimmy@gmail.com",
                                           email="justjoinedjimmy@gmail.com")
        phantom.consume_identity(jimmy)
        
        # Make sure we can still see the old user exercises
        shouldbejimmy = models.UserData.get_from_user_id("justjoinedjimmy@gmail.com")
        user_exercises = models.UserExercise.get_for_user_data(shouldbejimmy).fetch(100)
        self.assertEqual(len(exercises), len(user_exercises))
        for ue in user_exercises:
            self.assertEqual(7, ue.total_done)
