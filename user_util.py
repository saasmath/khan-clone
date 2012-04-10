"""
Utilities for handling user accounts.

Among other things, this file provides access-control decorators.
All handlers that derive from request_handler.py's RequestHandler
must decorate their get() and post() methods with one of these
decorators.

Here are the decorators that you can use:
   @open_access
   @moderator_only
   @developer_only
   @admin_only
   @manual_access_checking

@manual_access_checking means that the get()/post() routine you are
writing manually checks that the access is allowed.  Use sparingly!
"""

from functools import wraps
import logging
import urllib

from google.appengine.api import users

import request_cache
from app import App

def _go_to_login(handler, why):
    '''Redirects the user to the login page, and logs the access attempt.'''
    user_data = user_models.UserData.current()
    if user_data:
        logging.warning("Attempt by %s to access %s page"
                        % (user_data.user_id, why))
    # can't import util here because of circular dependencies
    url = "/login?continue=%s" % urllib.quote(handler.request.uri)
    return handler.redirect(url)


def open_access(method):
    '''Decorator that allows anyone to access this page.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        return method(self, *args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'open-access'   # for sanity checks
    return wrapper


# TODO(csilvers): add login_required, with
# is_current_user_logged_in: users.is_current_user_admin() or user_data is not None and also 'not user_data.is_demo'.  If user_data.is_demo, do:
#    self.redirect(util.create_logout_url(self.request.uri))

# TODO(csilvers): add login_required_something(demo_user_allowed=False)
# Also maybe something with phantom users?

@request_cache.cache()
def is_current_user_developer():
    user_data = user_models.UserData.current()
    return user_data and (users.is_current_user_admin() or
                          user_data.developer)

def developer_only(method):
    '''Decorator checking that users of a request are register as a developer.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_developer():
            return method(self, *args, **kwargs)
        else:
            return _go_to_login(self, "admin-only")

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'developer-only'   # checked in RequestHandler
    return wrapper

@request_cache.cache()
def is_current_user_moderator():
    user_data = user_models.UserData.current()
    return user_data and (users.is_current_user_admin() or
                          user_data.moderator or user_data.developer)

def moderator_only(method):
    '''Decorator checking that users of a request is registered as a moderator.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_moderator():
            return method(self, *args, **kwargs)
        else:
            return _go_to_login(self, "moderator-only")

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'moderator-only'   # checked in RequestHandler
    return wrapper

@request_cache.cache()
def is_current_user_admin():
    # Make sure current UserData exists as well as is_current_user_admin
    # because UserData properly verifies xsrf token.
    # TODO(csilvers): have this actually do xsrf checking for non-/api/ calls?
    #                 c.f. api/auth/auth_util.py:allow_cookie_based_auth()
    #                 If so, change the decorators to call ensure_xsrf_cookie.
    user_data = user_models.UserData.current()
    return user_data and users.is_current_user_admin()

def admin_only(method):
    '''Decorator checking that users of a request have an admin account.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_admin():
            return method(self, *args, **kwargs)
        else:
            return _go_to_login(self, "admin-only")

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'admin-only'   # checked in RequestHandler
    return wrapper

def manual_access_checking(method):
    '''Decorator that documents the method will do its own access checking.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        return method(self, *args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'manual-access'   # checked in RequestHandler
    return wrapper


def is_current_user(user_data):
    current_user_data = user_models.UserData.current()
    return (current_user_data and
            current_user_data.user_id == user_data.user_id)


# This isn't an access-control method, but is still useful.
def dev_server_only(method):
    '''Decorator that prevents a handler from working in production'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if App.is_dev_server:
            return method(self, *args, **kwargs)
        else:
            user_data = user_models.UserData.current()
            user_id = user_data.user_id or None
            logging.warning(
                "Attempt by %s to access production restricted page" % user_id)

            self.response.clear()
            self.response.set_status(501)  # not implemented
            self.response.set_message = "Method only allowed on dev server"
            return

    return wrapper

# Put down here to avoid circular-import problems.
# See http://effbot.org/zone/import-confusion.htm
import user_models
