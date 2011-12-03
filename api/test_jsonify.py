""" Unit tests for jsonify functionality """

import unittest
from jsonify import camel_casify

class JsonifyTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_camel_casing(self):
        self.assertEqual("", camel_casify(""))
        self.assertEqual("foo", camel_casify("foo"))
        self.assertEqual("fooBar", camel_casify("foo_bar"))
        self.assertEqual("fooBarJoeRalph", camel_casify("foo_bar_joe_ralph"))
        self.assertEqual("hypens-confuse-me", camel_casify("hypens-confuse-me"))
        self.assertEqual("trailingDoesntMatter_", camel_casify("trailing_doesnt_matter_"))
