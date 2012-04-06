"""Tests of all the handlers in v1.py.

This includes end-to-end tests of all the handlers in v1.  (It's a
rather slow test because of that.)  Basically, it sends off a url
request and makes sure the response is sane.  end-to-end tests require a
running appengine instance: it will start an instance on an unused port.
"""

from testutil import handler_test_utils
from testutil import oauth_test_client
try:
    import unittest2 as unittest     # python 2.5
except ImportError:
    import unittest                  # python 2.6+


def setUpModule():
    handler_test_utils.start_dev_appserver()

def tearDownModule():
    handler_test_utils.stop_dev_appserver()


class V1EndToEndTest(unittest.TestCase):
    def fetch(self, path):
        """Input is, e.g., '/api/v1/users'."""
        return oauth_test_client.fetch_via_oauth(
            handler_test_utils.appserver_url + path)

    def testUser(self):
        r = self.fetch('/api/v1/user')    
        self.assertTrue("user_id" in r, r)
