import pbkdf2
import datetime

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
