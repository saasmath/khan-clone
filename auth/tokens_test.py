from __future__ import absolute_import

from app import App
from agar.test import BaseTest
import auth.tokens as tokens
import datetime
import models
import random
import testutil
import unittest2

class TimestampTests(unittest2.TestCase):
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

class CookieTests(BaseTest):
    def setUp(self):
        super(CookieTests, self).setUp()
        self.orig_recipe_key = App.cookie_recipe_key
        App.cookie_recipe_key = 'secret recipe'

    def tearDown(self):
        App.cookie_recipe_key = self.orig_recipe_key
        super(CookieTests, self).tearDown()

    def make_user(self, user_id, credential_version):
        u = models.UserData.insert_for(user_id, user_id)
        u.credential_version = credential_version
        u.put()
        return u

    def test_cookie_expires_properly(self):
        clock = testutil.MockDatetime()
        u = self.make_user("userid1", "credential version 0")
        cookie = tokens.mint_cookie_for_user(u, clock)

        time_to_expiry = datetime.timedelta(30)
        self.assertTrue(tokens.validate_cookie(u, cookie, time_to_expiry, clock))

        # The day before expiry
        clock.advance_days(29)
        self.assertTrue(tokens.validate_cookie(u, cookie, time_to_expiry, clock))

        # Right at expiring point!
        clock.advance_days(1)
        self.assertTrue(tokens.validate_cookie(u, cookie, time_to_expiry, clock))

        # Tick - it's now stale.
        clock.advance(datetime.timedelta(seconds=1))
        self.assertFalse(tokens.validate_cookie(u, cookie, time_to_expiry, clock))

    def test_cookie_invalidates_properly(self):
        clock = testutil.MockDatetime()
        u = self.make_user("userid1", "credential version 0")
        cookie = tokens.mint_cookie_for_user(u, clock)

        time_to_expiry = datetime.timedelta(30)
        self.assertTrue(tokens.validate_cookie(u, cookie, time_to_expiry, clock))

        # Pretend the user changed her password.
        u.credential_version = "credential version 1"
        u.put()
        self.assertFalse(tokens.validate_cookie(u, cookie, time_to_expiry, clock))

