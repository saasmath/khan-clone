import auth
from agar.test import BaseTest
import random

class HashingTests(BaseTest):
    def test_hashing_is_unique(self):
        passwords = ['password',
                     'password1',
                     'thequickbrownfoxjumpsoverthelazydog',
                     'i4m$01337']
        random.seed(0)
        hashes = [auth.hash_password(pw, str(random.getrandbits(64)))
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
            hash = auth.hash_password(pw, salt)
            self.assertTrue(auth.validate_password(pw, salt, hash))
            self.assertFalse(auth.validate_password(pw + 'x', salt, hash))
