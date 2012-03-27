from __future__ import absolute_import

from cookie_util import set_request_cookie
import Cookie
import auth.tokens
import logging
import models
import os

# The cookie name for the unsecure (http) authentication cookie for password-
# based logins.
AUTH_COOKIE_NAME = 'KAID'

# The cookie set when the user is detected to be under13, and we need them
# locked out in accordance to COPPA
U13_COOKIE_NAME = 'u13'

def get_user_from_khan_cookies():
    cookies = None
    try:
        cookies = Cookie.BaseCookie(os.environ.get('HTTP_COOKIE', ''))
    except Cookie.CookieError, error:
        logging.critical("Ignoring Cookie Error: '%s'" % error)
        return None

    morsel = cookies.get(AUTH_COOKIE_NAME)
    if morsel and morsel.value:
        token_value = morsel.value
        token = auth.tokens.AuthToken.for_value(token_value)
        if not token:
            return None
        user_data = models.UserData.get_from_user_id(token.user_id)
        if user_data and token.is_valid(user_data):
            return token.user_id
    return None

def set_auth_cookie(handler, user, auth_token=None):
    """ Issues a Set-Cookie directive with the appropriate auth_token for
    the user.
    
    This will also set the cookie for the current request, so that subsequent
    calls to UserData.current() will point to the specified user.
    
    """

    if auth_token is None:
        auth_token = auth.tokens.AuthToken.for_user(user)
    else:
        pass # TODO(benkomalo): do we want to validate the auth token if passed?
    max_age = auth.tokens.AuthToken.DEFAULT_EXPIRY_SECONDS

    handler.set_cookie(AUTH_COOKIE_NAME,
                       value=auth_token.value,
                       max_age=max_age,
                       path='/',
                       domain=None,
                       secure=False,
                       httponly=True)
    set_request_cookie(AUTH_COOKIE_NAME, auth_token)

def set_under13_cookie(handler):
    handler.set_cookie(U13_COOKIE_NAME, value="1")

