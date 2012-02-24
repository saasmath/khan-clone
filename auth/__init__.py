import pbkdf2

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
