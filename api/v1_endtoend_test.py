"""Tests of all the handlers in v1.py.

This includes end-to-end tests of all the handlers in v1.  (It's a
rather slow test because of that.)  Basically, it sends off a url
request and makes sure the response is sane.  end-to-end tests require a
running appengine instance: it will start an instance on an unused port.
"""

from testutil import handler_test_utils
from testutil import oauth_test_client
from testutil import testsize
try:
    import unittest2 as unittest     # python 2.5
except ImportError:
    import unittest                  # python 2.6+


@testsize.large()
def setUpModule():
    handler_test_utils.start_dev_appserver(db='testutil/test_db.sqlite')


def tearDownModule():
    handler_test_utils.stop_dev_appserver()


class V1EndToEndTest(unittest.TestCase):
    def fetch(self, path):
        """path is e.g. '/api/v1/users'. Does a lot, so makes a test large."""
        return oauth_test_client.fetch_via_oauth(
            handler_test_utils.appserver_url + path)

    def assertIn(self, needle, haystack):
        self.assertTrue(needle in haystack,
                        'Did not find "%s" in "%s"' % (needle, haystack))

    @testsize.large()
    def test_user(self):
        """Test that the result is json and has the appropriate fields."""
        r = self.fetch('/api/v1/user')    
        self.assertIn("user_id", r)

    @testsize.large()
    def test_topics__with_content(self):
        r = self.fetch('/api/v1/topics/with_content')
        # Topic-version 11 (the default) appends '[early]' to all titles.
        self.assertIn("[late]", r)
        self.assertIn("standalone_title", r)

    def test_topicversion__version__topics__with_content(self):
        """2 is the non-default version in our test db."""
        r = self.fetch('/api/v1/topicversion/2/topics/with_content')
        # Topic-version 2 appends '[early]' to all titles.
        self.assertIn("[early]", r)
