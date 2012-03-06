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
        
        App.is_dev_server = False
        self.orig_host = None
        
    def stub_server_name(self, stubbed_name):
        if os.environ.has_key('HTTP_HOST'):
            self.orig_host = os.environ['HTTP_HOST']
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
