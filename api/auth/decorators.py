from functools import wraps

from google.appengine.api import users

import flask
from flask import request

from api.auth.auth_util import oauth_error_response, unauthorized_response
from api.auth.auth_models import OAuthMap

from oauth_provider.decorators import is_valid_request, validate_token
from oauth_provider.oauth import OAuthError

import user_util
import util
import os
import logging


def verify_and_cache_oauth_or_cookie(request):
    """ For a given request, try to oauth-verify or cookie-verify it.

    If the request has a valid oauth token, we store all the auth
    info in a per-request global (for easy access) and return.

    If the request does not have a valid oauth token, but has a valid
    http cookie *and* a valid xsrf token, return.

    Otherwise -- including the cases where there is an oauth token or
    cookie but they're not valid, raise an OAuthError of one form or
    another.

    This function is designed to be idempotent: it's safe (and fast)
    to call multiple times on the same request.  It caches enough
    per-request information to avoid repeating expensive work.

    Arguments:
       request: A 'global' flask var holding the current active request.

    Raises:
       OAuthError: are not able to authenticate the current user.
         (Note we give OAuthError even when we're failing the
         cookie-based request, which is a bit of abuse of terminology
         since there's no oauth involved in that step.)
    """
    if hasattr(flask.g, "oauth_map"):
        # Already called this routine and succeeded, so no need to call again.
        return

    # is_valid_request() verifies this request has something in it
    # that looks like an oauth token.
    if is_valid_request(request):
        consumer, token, parameters = validate_token(request)
        if (not consumer) or (not token):
            raise OAuthError("Not valid consumer or token")

        # Store the OAuthMap containing all auth info in the request
        # global for easy access during the rest of this request.
        # We do this now because get_current_user_id() accesses oauth_map.
        flask.g.oauth_map = OAuthMap.get_from_access_token(token.key_)

        if not util.get_current_user_id():
            # If our OAuth provider thinks you're logged in but the
            # identity providers we consume (Google/Facebook)
            # disagree, we act as if our token is no longer valid.
            del flask.g.oauth_map
            raise OAuthError("Unable to get current user from oauth token")

        # (We can do all the other global-setting after get_current_user_id.)
        # Store enough information from the consumer token that we can
        # do anointed checks.
        # TODO(csilvers): is it better to just store all of
        # 'consumer'? Seems too big given we just need to cache this
        # one piece of information right now.
        flask.g.is_anointed = consumer.anointed

    elif util.allow_cookie_based_auth():
        # TODO(csilvers): this duplicates a lot of calls
        # (get_current_user_id calls allow_cookie_based_auth too).
        # Simplify.
        if not util.get_current_user_id():
            logging.warning("Cookie: %s" % os.environ.get('HTTP_COOKIE',''))
            raise OAuthError("Unable to read user value from cookies/oauth map")

    else:
        raise OAuthError("Invalid parameters to Oauth request")


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_and_cache_oauth_or_cookie(request)
        except OAuthError, e:
            return oauth_error_response(e)

        if not user_util.is_current_user_admin():
            return unauthorized_response()
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'admin-required'   # checked in api.route()
    return wrapper

def developer_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_and_cache_oauth_or_cookie(request)
        except OAuthError, e:
            return oauth_error_response(e)

        if not user_util.is_current_user_developer():
            return unauthorized_response()
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'developer-required'   # checked in api.route()
    return wrapper

def moderator_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_and_cache_oauth_or_cookie(request)
        except OAuthError, e:
            return oauth_error_response(e)

        if not user_util.is_current_user_moderator():
            return unauthorized_response()
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'moderator-required'   # checked in api.route()
    return wrapper
    
def login_required(func):
    """ Decorator for validating an authenticated request.

    Checking oauth/cookie is the way to tell whether an API client is
    'logged in', since they can only have gotten an oauth token (or
    cookie token) via the login process.

    Note that phantom users with exercise data is considered
    a valid user.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_and_cache_oauth_or_cookie(request)
        except OAuthError, e:
            return oauth_error_response(e)
        # Request validated, proceed with the method.
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'oauth-required'   # checked in api.route()
    return wrapper

def open_access(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # We try to read the oauth info, so we have access to login
        # data if the user *does* happen to be logged in, but if
        # they're not we don't worry about it.
        try:
            verify_and_cache_oauth_or_cookie(request)
        except OAuthError, e:
            pass
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'open-access'   # checked in api.route()
    return wrapper

def manual_access_checking(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # For manual_access_checking we don't even try to read the
        # oauth data -- that's up for the handler to do itself.  This
        # makes manual_access_checking appropriate for handlers that
        # are part of the oauth-authentication process itself.
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'manual-access'   # checked in api.route()
    return wrapper


def anointed_oauth_consumer_only(func):
    """ Check that if a client is an oauth client, it's an 'anointed' one.

    This is a bit different from user authentication -- it only cares
    about the oauth *consumer* token.  That is, we don't care who the
    user is, we care what app (or script, etc) they are using to make
    this API call.  Some apps, such as the Khan iPad app, are
    'annointed', and have powers that normal API callers don't.

    NOTE: If the client is accessing via cookies and not via oauth, we
    always succeed.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # This sets flask.g.is_anointed, though only if the
            # request was an oauth request (and not a cookie request).
            # So for oauth requests, we're always using
            # flask.g.is_anointed, and for cookie requests, we're
            # always using the default value (3rd arg to getattr).
            if is_valid_request(request):   # only check if we're an oauth req.
                verify_and_cache_oauth_or_cookie(request)
            if not getattr(flask.g, "is_anointed", True):
                raise OAuthError("Consumer access denied.")
        except OAuthError, e:
            return oauth_error_response(e)
        return func(*args, **kwargs)
        
    return wrapper
