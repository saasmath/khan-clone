from __future__ import absolute_import

import Cookie
import auth.tokens
import logging
import models
import os

# The cookie name for the unsecure (http) authentication cookie for password-
# based logins.
AUTH_COOKIE_NAME = 'KAID'

def get_user_from_khan_cookies():
    cookies = None
    try:
        cookies = Cookie.BaseCookie(os.environ.get('HTTP_COOKIE', ''))
    except Cookie.CookieError, error:
        logging.critical("Ignoring Cookie Error: '%s'" % error)
        return None

    morsel = cookies.get(AUTH_COOKIE_NAME)
    if morsel and morsel.value:
        token = morsel.value
        user_id = auth.tokens.user_id_from_token(token)
        if user_id:
            user_data = models.UserData.get_from_user_id(user_id)
            if user_data and auth.tokens.validate_token(user_data, token):
                return user_id
    return None


def set_auth_cookie(handler, user):
    auth_token = auth.tokens.mint_token_for_user(user)
    max_age = auth.tokens.DEFAULT_TOKEN_EXPIRY_SECONDS

    # Success! log them in
    handler.set_cookie(AUTH_COOKIE_NAME,
                       value=auth_token,
                       max_age=max_age,
                       path='/',
                       domain=None,
                       secure=False,
                       # TODO(benkomalo): make this httponly!
                       # STOPSHIP - this is just easier for testing for now
                       httponly=False)


