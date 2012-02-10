#!/usr/bin/env python

import datetime
import unittest
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

class GAEModelTestCase(unittest.TestCase):
    """ A test case that stubs out appengine's persistence layers in setUp.

    Subclasses can inherit from this if they wish to test models, but don't
    forget to call the superclass's setUp and tearDown methods if you
    override them.

    """
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)

        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

class MockDatetime(object):
    """ A utility for mocking out the current time.

    Exposes methods typically found in Python's normal datetime library,
    and attempts to be compatible with all API's there so that it
    can be a drop-in for datetime.
    """

    def __init__(self, initial_value_utc=None):
        self.value = initial_value_utc or datetime.datetime.utcfromtimestamp(0)

    def utcnow(self):
        """ Returns a Python datetime.datetime object for the current clock's
        value.

        """
        return self.value

    def advance(self, delta):
        """ Advances by a datetime.timedelta """
        self.value = self.value + delta

    def advance_days(self, days):
        """ Advances by a specified number of days """
        self.value = self.value + datetime.timedelta(days)


