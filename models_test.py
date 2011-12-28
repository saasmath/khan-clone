# /usr/bin/env python

import models
import unittest

class UsernameTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_user_name_fuzzy_match(self):
        """ Tests user name search can ignore periods properly. """
        def k(n):
            return models.UniqueUsername.build_key_name(n)

        self.assertEqual(k('mr.pants'), k('mrpants'))
        self.assertEqual(k('mr.pants...'), k('mrpants'))
        self.assertEqual(k('mrpants'), k('mrpants'))
        self.assertEqual(k('MrPants'), k('mrpants'))

    def validate(self, username):
        return models.UniqueUsername.is_valid_username(username)

    def test_bad_user_name_fails_validation(self):
        self.assertFalse(self.validate(''))
        self.assertFalse(self.validate('a')) # Too short
        self.assertFalse(self.validate('aaaa')) # Still too short
        self.assertFalse(self.validate('4scoresand7years')) # Must start with letter
        self.assertFalse(self.validate('.dotsarebadtoo'))
        self.assertFalse(self.validate('!nvalid'))
        self.assertFalse(self.validate('B@dCharacters'))
        self.assertFalse(self.validate('I cannot read instructions'))
        self.assertFalse(self.validate(u'h\u0400llojello')) # Cyrillic chars

    def test_good_user_name_validates(self):
        self.assertTrue(self.validate('poopybutt'))
        self.assertTrue(self.validate('mrpants'))
        self.assertTrue(self.validate('instructionsareeasy'))
        self.assertTrue(self.validate('coolkid1983'))

