import pbkdf2
import hmac
import hashlib
import datetime
import base64
from app import App

def hash_password(raw_password, salt):
    """ Generates a strong one-way hash (effective 192 bits) for the
    specified password and salt.
    Both arguments are expected to be strings
    """
    return pbkdf2.crypt(raw_password, salt, iterations=5000)

def validate_password(raw_password, salt, expected):
    """ Returns whether or not the raw_password+salt combination hashes
    to the same value as expected, assuming it used hash_password. """
    return hash_password(raw_password, salt) == expected


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
    except Exception, e:
        return None
    return result

def _make_cookie_signature(user_id,
                           credential_version,
                           timestamp,
                           key=None):
    """ Generates a signature to be embedded inside of a cookie.
    This signature serves two goals. The first is to validate the rest of
    the contents of the cookie, much like a simple hash. The second is to
    also encode a unique, user-specific string that can be invalidated if the
    user changes her password (the credential_version).
    """

    payload = "\n".join([user_id, credential_version, timestamp])
    secret = key or App.cookie_recipe_key
    return hmac.new(secret, payload, hashlib.sha256).digest()

def mint_cookie_for_user(user_data, clock=None):
    """ Generates a base64 encoded value to be used as an authentication cookie
    for a user.

    The cookie will contain the identity of the user and timestamp of creation,
    so expiry logic is externalized and controlled at a higher level.
    """
    user_id = user_data.user_id
    timestamp = _to_timestamp((clock or datetime.datetime).utcnow())
    credential_version = user_data.credential_version
    signature = _make_cookie_signature(user_id, timestamp, credential_version)
    return base64.b64encode("\n".join([user_id, timestamp, signature]))

def validate_cookie(user_data, cookie, time_to_expiry=None, clock=None):
    """ Determines whether or not the cookie is a valid authentication token
    for the specified user.
    
    If time_to_expiry is unspecified, a default of 30 days is used.
    """

    try:
        contents = base64.b64decode(cookie)
    except TypeError:
        # Not proper base64 encoded value.
        return False

    user_id, timestamp, signature = contents.split("\n")
    if user_id != user_data.user_id:
        return False

    if not time_to_expiry:
        time_to_expiry = datetime.timedelta(days=30)
    dt = _from_timestamp(timestamp)
    now = (clock or datetime.datetime).utcnow()
    if not dt or (now - dt) > time_to_expiry:
        return False

    # Contents look good - now make sure it validates against the sig.
    expected = _make_cookie_signature(user_data.user_id,
                                      timestamp,
                                      user_data.credential_version)
    return expected == signature
