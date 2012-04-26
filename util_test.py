import os
import util
from app import App

try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TestUrl(unittest.TestCase):
    def setUp(self):
        super(TestUrl, self).setUp()

        self.orig_app_dev_server = App.is_dev_server
        App.is_dev_server = False
        self.orig_host = None

    def tearDown(self):
        App.is_dev_server = self.orig_app_dev_server

    def stub_server_name(self, stubbed_name):
        if os.environ.has_key('HTTP_HOST'):
            self.orig_host = os.environ['HTTP_HOST']
        else:
            self.orig_host = None
        os.environ['HTTP_HOST'] = stubbed_name

    def restore_server_name(self):
        if self.orig_host:
            os.environ['HTTP_HOST'] = self.orig_host
        else:
            del os.environ['HTTP_HOST']

    def test_url_securing_on_normal_url(self):
        self.stub_server_name('www.khanacademy.org')
        # relative url
        self.assertEqual("https://khan-academy.appspot.com/login",
                         util.secure_url("/login"))

        # Absolute url (gets re-written to appspot)
        self.assertEqual("https://khan-academy.appspot.com/login",
                         util.secure_url("http://www.khanacademy.org/login"))
        self.restore_server_name()

    def test_url_insecuring_on_normal_url(self):
        self.stub_server_name('www.khanacademy.org')

        # relative URL
        self.assertEqual("http://www.khanacademy.org/postlogin",
                         util.insecure_url("/postlogin"))

        # absolute URL
        self.assertEqual("http://www.khanacademy.org/postlogin",
                         util.insecure_url("https://www.khanacademy.org/postlogin"))
        self.restore_server_name()

    def test_url_securing_on_appspot_url(self):
        self.stub_server_name("non-default.khan-academy.appspot.com")
        # relative url
        self.assertEqual("https://non-default.khan-academy.appspot.com/foo",
                         util.secure_url("/foo"))
        # Absolute url
        self.assertEqual("https://non-default.khan-academy.appspot.com/foo",
                         util.secure_url("http://non-default.khan-academy.appspot.com/foo"))
        self.restore_server_name()

    def test_url_insecuring_on_appspot_url(self):
        self.stub_server_name("non-default.khan-academy.appspot.com")
        # relative url
        self.assertEqual("http://non-default.khan-academy.appspot.com/foo",
                         util.insecure_url("/foo"))
        # Absolute url
        self.assertEqual("http://non-default.khan-academy.appspot.com/foo",
                         util.insecure_url("https://non-default.khan-academy.appspot.com/foo"))
        self.restore_server_name()

    def test_detection_of_ka_urls(self):
        def is_ka_url(url):
            return util.is_khanacademy_url(url)

        self.stub_server_name("www.khanacademy.org")
        self.assertTrue(is_ka_url("/relative/url"))
        self.assertTrue(is_ka_url(util.absolute_url("/relative/url")))
        self.assertTrue(is_ka_url(util.static_url("/images/foo")))
        self.assertTrue(is_ka_url("http://www.khanacademy.org"))
        self.assertTrue(is_ka_url("http://smarthistory.khanacademy.org"))
        self.assertTrue(is_ka_url("http://www.khanacademy.org/"))
        self.assertTrue(is_ka_url("http://www.khanacademy.org/foo"))
        self.assertTrue(is_ka_url("https://khan-academy.appspot.com"))
        self.assertTrue(is_ka_url("http://non-default.khan-academy.appspot.com"))
        self.assertTrue(is_ka_url("https://non-default.khan-academy.appspot.com"))
        self.restore_server_name()

    def test_detection_of_non_ka_urls(self):
        self.assertFalse(util.is_khanacademy_url("http://evil.com"))
        self.assertFalse(util.is_khanacademy_url("https://khanacademy.phising.com"))

