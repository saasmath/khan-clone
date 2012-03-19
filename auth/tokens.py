from app import App
import base64
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

class BaseToken(object):
    """ An abstract token class with the general requirement that token values
    cannot be forged and should be unique for each user, and can expire.

    Note that instances may be created that are invalid. Clients must check
    is_valid() to ensure the contents of the token are valid.
    
    Subclasses should provide a staticmethod _make_token_signature, which
    will deal with the specifics of each token type's security requirements.

    """
    
    def __init__(self, user_id, timestamp, signature):
        self.user_id = user_id
        self.timestamp = timestamp
        self.signature = signature
        self._value_internal = None

    @property
    def type(self):
        raise Exception("Not implemented in base class")

    @classmethod
    def for_value(cls, token_value):
        """ Parses a string intended to be an token value.
        
        Returns None if the string is invalid, and an instance of BaseToken
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
        if len(parts) != 4:
            # Wrong number of parts / malformed.
            logging.info("Tried to decode malformed auth token")
            return None
        type, user_id, timestamp, signature = parts
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
        """ Determines if the token is valid for a given user. """
        if self.user_id != user_data.user_id:
            return False

        expected = self._make_token_signature(user_data, self.timestamp)
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
            self._value_internal = base64.b64encode("\n".join([self.type,
                                                               self.user_id,
                                                               self.timestamp,
                                                               self.signature]))
        return self._value_internal


class AuthToken(BaseToken):
    """ A secure token used to authenticate a user that has a password set.

    Note that instances may be created that are invalid. Clients must check
    is_valid() to ensure the contents of the token are valid.
    
    """

    @property
    def type(self):
        return "auth"

    @staticmethod
    def for_user(user_data, clock=None):
        """ Given a user with a password set, create a new, valid, token
        for that user.

        Will raise an Exception if the user has never set a password.

        """

        if not user_data.credential_version:
            raise Exception("Cannot mint an auth token for user [%s] "
                            " - no credential version" % user_data.user_id)

        timestamp = _to_timestamp((clock or datetime.datetime).utcnow())
        signature = AuthToken._make_token_signature(
                user_data,
                timestamp)
        return AuthToken(user_data.user_id, timestamp, signature)

    @staticmethod
    def _make_token_signature(user_data, timestamp, key=None):
        """ Generates a signature to be embedded inside of a secure token.
    	This signature serves two goals. The first is to validate the rest of
    	the contents of the token, much like a simple hash. The second is to
        also encode a unique, user-specific string that can be invalidated if
        the user changes her password (the credential_version).

        """

        payload = "\n".join([user_data.user_id,
                             user_data.credential_version,
                             timestamp])
        secret = key or App.token_recipe_key
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

