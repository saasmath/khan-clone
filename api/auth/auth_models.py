import datetime
import logging

from google.appengine.ext import db

import auth.tokens


# OAuthMap creates a mapping between our OAuth credentials and our identity providers'.
class OAuthMap(db.Model):

    # Our tokens
    request_token = db.StringProperty()
    request_token_secret = db.StringProperty()
    access_token = db.StringProperty()
    access_token_secret = db.StringProperty()
    verifier = db.StringProperty()

    # Facebook tokens
    facebook_authorization_code = db.StringProperty()
    facebook_access_token = db.StringProperty()

    # Google tokens
    google_request_token = db.StringProperty()
    google_request_token_secret = db.StringProperty()
    google_access_token = db.StringProperty()
    google_access_token_secret = db.StringProperty()
    google_verification_code = db.StringProperty()

    # Auth token (redeemed via username/password combo)
    khan_auth_token = db.StringProperty(indexed=False)

    # Our internal callback URL
    callback_url = db.StringProperty()

    # Our view options for interacting w/ identity providers
    # that provide special views for mobile, etc
    view = db.StringProperty(default="normal")

    # Expiration
    expires = db.DateTimeProperty()

    def uses_facebook(self):
        return self.facebook_authorization_code

    def uses_google(self):
        return self.google_request_token

    def uses_password(self):
        return self.khan_auth_token is not None

    def is_expired(self):
        return self.expires and self.expires < datetime.datetime.now()

    def is_mobile_view(self):
        return self.view == "mobile"

    def callback_url_with_request_token_params(self, include_verifier = False):
        params_callback = {
            "oauth_token": self.request_token, 
            "oauth_token_secret": self.request_token_secret
        }
        
        if include_verifier and self.verifier:
            params_callback["oauth_verifier"] = self.verifier

        return append_url_params(self.callback_url, params_callback)

    def _get_authenticated_user_info(self, id_only=False):
        """ Gets the UserData or user_id for this OAuthMap, if it's still
        valid.
        
        """

        from models import UserData

        user_id = None
        email = None

        if self.uses_google():
            user_id, email = get_google_user_id_and_email_from_oauth_map(self)
        elif self.uses_facebook():
            user_id = get_facebook_user_id_from_oauth_map(self)
            email = user_id
        elif self.uses_password():
            user_data = auth.tokens.AuthToken.get_user_for_value(
                    self.khan_auth_token, UserData.get_from_user_id)
            # Note that we can't "create" a user by username/password logins
            # via the oauth flow.
            if not id_only:
                return user_data
            elif user_data:
                user_id, email = user_data.user_id, user_data.email

        if id_only:
            return user_id

        return (UserData.get_from_user_id(user_id) or
                UserData.get_from_db_key_email(email) or
                UserData.insert_for(user_id, email))

    def get_user_id(self):
        """ Returns the authenticated UserData for this OAuthMap
        if this OAuthMap still refers to an authenticated user.

        If the OAuth process is incomplete, or the credentials have been
        invalidated by the external Oauth providers or expired for any other
        reason, this will return None

        """
        return self._get_authenticated_user_info(id_only=True)

    def get_user_data(self):
        """ Returns the authenticated user_id for the user for this OAuthMap
        if this OAuthMap still refers to an authenticated user.

        If the OAuth process is incomplete, or the credentials have been
        invalidated by the external Oauth providers or expired for any other
        reason, this will return None

        """
        return self._get_authenticated_user_info(id_only=False)

    @staticmethod
    def if_not_expired(oauth_map):
        if oauth_map and oauth_map.is_expired():
            logging.warning("Not returning expired OAuthMap.")
            return None
        return oauth_map

    @staticmethod
    def get_by_id_safe(request_id):
        if not request_id:
            return None
        try:
            parsed_id = int(request_id)
        except ValueError:
            return None
        return OAuthMap.if_not_expired(OAuthMap.get_by_id(parsed_id))

    @staticmethod
    def get_from_request_token(request_token):
        if not request_token:
            return None
        return OAuthMap.if_not_expired(OAuthMap.all().filter("request_token =", request_token).get())

    @staticmethod
    def get_from_access_token(access_token):
        if not access_token:
            return None
        return OAuthMap.if_not_expired(OAuthMap.all().filter("access_token =", access_token).get())

from api.auth.auth_util import append_url_params
from api.auth.google_util import get_google_user_id_and_email_from_oauth_map
from facebook_util import get_facebook_user_id_from_oauth_map
