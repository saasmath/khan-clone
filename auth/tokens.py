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

def _make_token_signature(user_id,
                          credential_version,
                          timestamp,
                          key=None):
    """ Generates a signature to be embedded inside of an auth token.
    This signature serves two goals. The first is to validate the rest of
    the contents of the token, much like a simple hash. The second is to
    also encode a unique, user-specific string that can be invalidated if the
    user changes her password (the credential_version).
    """

    payload = "\n".join([user_id, credential_version, timestamp])
    secret = key or App.token_recipe_key
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()

class AuthToken(object):
    """ A secure token used to authenticate a user.

    Note that instances may be created that are invalid. Clients must check
    is_valid() to ensure the contents of the token are valid.
    
    """

    def __init__(self, user_id, timestamp, signature):
        self.user_id = user_id
        self.timestamp = timestamp
        self.signature = signature
        self._value_internal = None
    
    @staticmethod
    def for_user(user_data, clock=None):
        if not user_data.credential_version:
            raise Exception("Cannot mint an auth token for user [%s] "
                            " - no credential version" % user_data.user_id)

        timestamp = _to_timestamp((clock or datetime.datetime).utcnow())
        signature = _make_token_signature(user_data.user_id,
                                          timestamp,
                                          user_data.credential_version)
        return AuthToken(user_data.user_id, timestamp, signature)
    
    @staticmethod
    def for_value(token_value):
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
        return AuthToken(user_id, timestamp, signature)
    
    DEFAULT_EXPIRY = datetime.timedelta(days=14)
    DEFAULT_EXPIRY_SECONDS = DEFAULT_EXPIRY.days * 86400

    def is_expired(self, time_to_expiry=DEFAULT_EXPIRY, clock=None):
        dt = _from_timestamp(self.timestamp)
        now = (clock or datetime.datetime).utcnow()
        return not dt or (now - dt) > time_to_expiry
    
    def is_authentic(self, user_data):
        if self.user_id != user_data.user_id:
            return False

        expected = _make_token_signature(user_data.user_id,
                                         self.timestamp,
                                         user_data.credential_version)
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

def user_id_from_token(token_value):
    """ Given an auth token, determine the user_id that it's supposed to belong
    to.
    
    Does not actually validate authenticity of the token - only well - formedness.
    Clients are expected to call validate_token when the CredentialedUser has
    been retrieved from the id.
    
    """

    token = AuthToken.for_value(token_value)
    return token.user_id

