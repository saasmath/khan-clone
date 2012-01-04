#!/user/bin/env python

import unittest
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

import models

class NicknamesTest(unittest.TestCase):

    def setUp(self):
        self.user_count = 0
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def assertSingleResult(self, expected, raw_query):
        matches = models.NicknameIndex.users_for_search(raw_query)
        self.assertEqual(1, len(matches),
                         "Expected exactly 1 result for \"%s\"" % raw_query)
        self.assertEqual(expected, matches[0])

    def make_user(self, nickname):
        u = models.UserData(key_name="key_%s" % self.user_count)
        u.user_id = "userid_%s" % self.user_count
        u.update_nickname(nickname)
        u.put()

        self.user_count += 1
        return u

    def test_retrieve_user_by_nickname(self):
        u = self.make_user('Fake User One')

        for raw_query in ['Fake', 'uSeR', 'ONE', 'fake user one']:
            self.assertSingleResult(u.user_id, raw_query)

        user_matches = models.NicknameIndex.users_for_search('does not exist')
        self.assertEqual(0, len(user_matches))

    def test_retrieval_order_agnostic(self):
        u = self.make_user('Firstname Middlename Lastname')

        # Order of tokens doesn't matter (name order differs by culture anyways)
        for raw_query in ['Lastname, Firstname',
                          'Firstname Lastname',
                          'lastname firstname middlename']:
            self.assertSingleResult(u.user_id, raw_query)

    def test_multi_user_search(self):
        han_solo = self.make_user('Han Solo')
        leia = self.make_user('Leia Organa Solo')
        jabba = self.make_user('Jabba the Hutt')

        for raw_query in ['Han Solo', 'Han']:
            self.assertSingleResult(han_solo.user_id, raw_query)

        for raw_query in ['Leia']:
            self.assertSingleResult(leia.user_id, raw_query)

        for raw_query in ['Jabba', 'the Hutt', 'jabba the HUTT']:
            self.assertSingleResult(jabba.user_id, raw_query)

        matches = models.NicknameIndex.users_for_search('Solo')
        self.assertEquals(2, len(matches))
        self.assertEquals(set([han_solo.user_id, leia.user_id]), set(matches))

    def test_partial_matches(self):
        self.make_user('Firstname Middlename Lastname')

        # Partial matches on a full search should _not_ be returned.
        for raw_query in ['lastn', 'firstname mid', 'firstname wronglast']:
            user_matches = models.NicknameIndex.users_for_search(raw_query)
            self.assertEqual(0, len(user_matches))
