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

def mint_token_for_user(user_data, clock=None):
    """ Generates a base64 encoded value to be used as an authentication token
    for a user, that can be used in things like cookies.

    The token will contain the identity of the user and timestamp of creation,
    so expiry logic is externalized and controlled at a higher level.
    """
    user_id = user_data.user_id
    timestamp = _to_timestamp((clock or datetime.datetime).utcnow())
    credential_version = user_data.credential_version
    if not credential_version:
        raise Exception("Cannot mint an auth token for user [%s] " +
                        " - no credential version" % user_id)
    signature = _make_token_signature(user_id, timestamp, credential_version)
    return base64.b64encode("\n".join([user_id, timestamp, signature]))

def validate_token(user_data, token, time_to_expiry=None, clock=None):
    """ Determines whether or not the token is a valid authentication token
    for the specified user.

    If time_to_expiry is unspecified, a default of 30 days is used.
    """

    try:
        contents = base64.b64decode(token)
    except TypeError:
        # Not proper base64 encoded value.
        logging.info("Tried to decode auth token that isn't base64 encoded")
        return False

    try:
        user_id, timestamp, signature = contents.split("\n")
    except Exception:
        # Wrong number of parts / malformed.
        logging.info("Tried to decode malformed auth token")
        return False

    if user_id != user_data.user_id:
        logging.info("Tried to decode auth token for different user." +
                     " requestor[%s] token[%s]" % (user_data.user_id, user_id))
        return False

    if not time_to_expiry:
        time_to_expiry = datetime.timedelta(days=30)
    dt = _from_timestamp(timestamp)
    now = (clock or datetime.datetime).utcnow()
    if not dt or (now - dt) > time_to_expiry:
        return False

    # Contents look good - now make sure it validates against the sig.
    expected = _make_token_signature(user_data.user_id,
                                      timestamp,
                                      user_data.credential_version)
    return expected == signature

