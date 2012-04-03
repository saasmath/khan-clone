from __future__ import absolute_import

from app import App
from agar.test import BaseTest
import auth.tokens as tokens
import datetime
import models
import testutil

try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TimestampTests(unittest.TestCase):
    def test_timestamp_creation(self):
        clock = testutil.MockDatetime()

        def assertDatetimeSerializes():
            now = clock.utcnow()
            timestamp = tokens._to_timestamp(now)
            self.assertEquals(now, tokens._from_timestamp(timestamp))

        assertDatetimeSerializes()
        clock.advance_days(1)
        assertDatetimeSerializes()
        clock.advance_days(30)
        assertDatetimeSerializes()
        clock.advance_days(366)
        assertDatetimeSerializes()
        clock.advance(datetime.timedelta(seconds=1))
        assertDatetimeSerializes()
        clock.advance(datetime.timedelta(microseconds=1))
        assertDatetimeSerializes()

class TokenTests(BaseTest):
    def setUp(self):
        super(TokenTests, self).setUp()
        self.orig_recipe_key = App.token_recipe_key
        App.token_recipe_key = 'secret recipe'

    def tearDown(self):
        App.token_recipe_key = self.orig_recipe_key
        super(TokenTests, self).tearDown()

    def make_user(self, user_id, credential_version):
        u = models.UserData.insert_for(user_id, user_id)
        u.credential_version = credential_version
        u.put()
        return u

    def test_token_expires_properly(self):
        clock = testutil.MockDatetime()
        u = self.make_user("userid1", "credential version 0")
        token = tokens.AuthToken.for_user(u, clock)

        time_to_expiry = datetime.timedelta(30)
        self.assertTrue(token.is_valid(u, time_to_expiry, clock))

        # The day before expiry
        clock.advance_days(29)
        self.assertTrue(token.is_valid(u, time_to_expiry, clock))

        # Right at expiring point!
        clock.advance_days(1)
        self.assertTrue(token.is_valid(u, time_to_expiry, clock))

        # Tick - it's now stale.
        clock.advance(datetime.timedelta(seconds=1))
        self.assertFalse(token.is_valid(u, time_to_expiry, clock))

    def test_token_invalidates_properly(self):
        clock = testutil.MockDatetime()
        u = self.make_user("userid1", "credential version 0")
        token = tokens.AuthToken.for_user(u, clock)

        time_to_expiry = datetime.timedelta(30)
        self.assertTrue(token.is_valid(u, time_to_expiry, clock))

        # Pretend the user changed her password.
        u.credential_version = "credential version 1"
        u.put()
        self.assertFalse(token.is_valid(u, time_to_expiry, clock))

    def test_auth_token_parses(self):
        clock = testutil.MockDatetime()
        u = self.make_user("userid1", "credential version 0")
        token = tokens.AuthToken.for_user(u, clock)
        
        parsed = tokens.AuthToken.for_value(token.value)
        time_to_expiry = datetime.timedelta(30)
        self.assertTrue(parsed.is_valid(u, time_to_expiry, clock))
