import auth
from google.appengine.ext import db
# TODO(benkomalo): use a stronger crypto random?
import random

class Credential(db.Model):
    """ An abstraction around a password for a given user.

    All Credential instances must have a UserData object as an ancestor to show
    association, and does not store actual username / email information itself.
    """

    hashed_pass = db.StringProperty(indexed=False)
    salt = db.StringProperty(indexed=False)

    @staticmethod
    def make_for_user(user_data, raw_password):
        salt = str(random.getrandbits(64))
        return Credential(parent=user_data,
                          hashed_pass=auth.hash_password(raw_password, salt),
                          salt=salt)

    @staticmethod
    def retrieve_for_user(user_data):
        return Credential.all().ancestor(user_data).get()

    def validate_password(self, raw_password):
        # TODO(benkomalo): shortcut this to check if raw_password isn't
        # even a valid password.
        return auth.hash_password(raw_password, self.salt) == self.hashed_pass
