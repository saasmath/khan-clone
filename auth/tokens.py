from __future__ import absolute_import

from app import App

import base64
import cookie_util
import datetime
import hashlib
import hmac
import logging

_FORMAT = "%Y%j%H%M%S"
def _to_timestamp(dt):
    return "%s.%s" % (dt.strftime(_FORMAT), dt.microsecond)

def _from_timestamp(s):
    if not s:
        return None
    main, ms = s.split('.')
    try:
        result = datetime.datetime.strptime(main, _FORMAT)
        result = result.replace(microsecond=int(ms))
    except Exception:
        return None
    return result

class BaseSecureToken(object):
    """ A base secure token used to identify and authenticate a user.

    Note that instances may be created that are invalid. Clients must check
    is_valid() to ensure the contents of the token are valid.
    
    Different token types may be created by extending and having subclasses
    override the method to generate the token signature.

    """

    def __init__(self, user_id, timestamp, signature):
        self.user_id = user_id
        self.timestamp = timestamp
        self.signature = signature
        self._value_internal = None
        
    @staticmethod
    def make_token_signature(user_data, timestamp):
        """ Subclasses should override this so to return a unique signature
        a user given a particular token type.

        """
        raise Exception("Not implemented in base class")

    @classmethod
    def for_user(cls, user_data, clock=None):
        """ Generate a secure token for a user. """

        timestamp = _to_timestamp((clock or datetime.datetime).utcnow())
        signature = cls.make_token_signature(
                user_data, timestamp)
        return cls(user_data.user_id, timestamp, signature)

    @classmethod
    def for_value(cls, token_value):
        """ Parses a string intended to be an secure token value.

        Returns None if the string is invalid, and an instance of the token
        otherwise. Note that this essentially only checks well-formedness,
        and the token itself may be expired or invalid so clients must call
        is_valid or equivalent to verify.
        
        """

        try:
            contents = base64.b64decode(token_value)
        except TypeError:
            # Not proper base64 encoded value.
            logging.info("Tried to decode auth token that isn't base64 encoded")
            return None

        parts = contents.split("\n")
        if len(parts) != 3:
            # Wrong number of parts / malformed.
            logging.info("Tried to decode malformed auth token")
            return None
        user_id, timestamp, signature = parts
        return cls(user_id, timestamp, signature)

    DEFAULT_EXPIRY = datetime.timedelta(days=14)
    DEFAULT_EXPIRY_SECONDS = DEFAULT_EXPIRY.days * 86400

    def is_expired(self, time_to_expiry=DEFAULT_EXPIRY, clock=None):
        """ Determines whether or not the specified token is expired.
        
        Note that tokens encapsulate timestamp on creation, so the application
        may change the expiry lengths at any time and invalidate historical
        tokens with such changes.
        
        """

        dt = _from_timestamp(self.timestamp)
        now = (clock or datetime.datetime).utcnow()
        return not dt or (now - dt) > time_to_expiry

    def is_authentic(self, user_data):
        """ Determines if the token is valid for a given user.
        
        Users may invalidate all existing auth tokens by changing his/her
        password.
        
        """
        if self.user_id != user_data.user_id:
            return False

        expected = self.make_token_signature(
                    user_data, self.timestamp)
        return expected == self.signature
    
    def is_valid(self, user_data,
                 time_to_expiry=DEFAULT_EXPIRY, clock=None):
        return (not self.is_expired(time_to_expiry, clock) and
                self.is_authentic(user_data))

    def __str__(self):
        return self.value
    
    def __unicode__(self):
        return self.value
    
    @property
    def value(self):
        if self._value_internal is None:
            self._value_internal = base64.b64encode("\n".join([self.user_id,
                                                               self.timestamp,
                                                               self.signature]))
        return self._value_internal

class AuthToken(BaseSecureToken):
    """ A secure token used to authenticate a user that has a password set.

    Note that instances may be created that are invalid. Clients must check
    is_valid() to ensure the contents of the token are valid.
    
    """
    @staticmethod
    def make_token_signature(user_data, timestamp):
        """ Generates a signature to be embedded inside of an auth token.
    	This signature serves two goals. The first is to validate the rest of
    	the contents of the token, much like a simple hash. The second is to
        also encode a unique user-specific string that can be invalidated if
        all existing tokens of the given type need to be invalidated.

        """

        payload = "\n".join([
                user_data.user_id,
                user_data.credential_version,
                timestamp
                ])
        secret = App.token_recipe_key
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

class GoogleUserToken(BaseSecureToken):
    """ A short-lived authentication token that can only be minted for signed
    in Google users. This is used to transfer identities of Google users
    securely.

    Since the cookie which identifies Google users on http requests (ACSID) is
    not verifiable by the appengine SDK on https requests, we mint a custom
    token so that it can be sent over https.

    """

    @staticmethod
    def make_token_signature(user_data, timestamp):
        # This signature design intentionally relies on the ACSID cookie so that
        # only valid ACSID values can be minted on http requests, and that same
        # valid ACSID must be match on the https response.
        google_cookie = cookie_util.get_google_cookie()
        payload = "\n".join([
                user_data.user_id,
                google_cookie,
                timestamp
                ])
        secret = App.token_recipe_key
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    # Force a short expiry for these tokens.
    DEFAULT_EXPIRY = datetime.timedelta(days=1)
    DEFAULT_EXPIRY_SECONDS = DEFAULT_EXPIRY.days * 86400

    def is_expired(self, time_to_expiry=DEFAULT_EXPIRY, clock=None):
        dt = _from_timestamp(self.timestamp)
        now = (clock or datetime.datetime).utcnow()
        return not dt or (now - dt) > time_to_expiry
