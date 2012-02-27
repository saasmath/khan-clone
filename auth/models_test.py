from __future__ import absolute_import

from agar.test.base_test import BaseTest
from app import App
import auth.tokens
import models

class CredentialTest(BaseTest):
    def setUp(self):
        super(CredentialTest, self).setUp()
        self.orig_recipe_key = App.token_recipe_key
        App.token_recipe_key = 'secret recipe'

    def tearDown(self):
        App.token_recipe_key = self.orig_recipe_key
        super(CredentialTest, self).tearDown()

    def make_user(self, email):
        u = models.UserData.insert_for(email, email)
        u.put()
        return u

    def test_password_validation(self):
        u = self.make_user('bob@example.com')

        # No pw yet. Nothing should pass
        self.assertFalse(u.validate_password('password'))

        u.set_password('Password1')
        self.assertFalse(u.validate_password('password'))
        self.assertTrue(u.validate_password('Password1'))

    def test_updating_password(self):
        u = self.make_user('bob@example.com')

        u.set_password('Password1')
        token = auth.tokens.mint_token_for_user(u)
        self.assertTrue(auth.tokens.validate_token(u, token))

        u.set_password('NewS3cr3t!')
        self.assertFalse(u.validate_password('Password1'))
        self.assertTrue(u.validate_password('NewS3cr3t!'))

