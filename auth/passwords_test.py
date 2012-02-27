from auth.passwords import *
import random
import unittest2

class HashingTests(unittest2.TestCase):
    def test_hashing_is_unique(self):
        passwords = ['password',
                     'password1',
                     'thequickbrownfoxjumpsoverthelazydog',
                     'i4m$01337']
        random.seed(0)
        hashes = [hash_password(pw, str(random.getrandbits(64)))
                  for pw in passwords]
        self.assertEquals(len(set(hashes)), len(passwords))

    def test_hashing_is_verifiable(self):
        passwords = ['password',
                     'password1',
                     'thequickbrownfoxjumpsoverthelazydog',
                     'i4m$01337']
        random.seed(0)
        for pw in passwords:
            salt = str(random.getrandbits(64))
            hash = hash_password(pw, salt)
            self.assertTrue(validate_password(pw, salt, hash))
            self.assertFalse(validate_password(pw + 'x', salt, hash))

