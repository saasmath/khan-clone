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

import app
import request_cache


class LoginFailedError(Exception): pass


def verify_login(admin_required,
                 developer_required,
                 moderator_required,
                 demo_user_allowed,
                 phantom_user_allowed):
    """Check if there is a current logged-in user fitting the given criteria.

    This function makes sure there is a current-logged in user, and
    the user is of the right type.  For instance, if
    demo_allowed==False, and the logged in user is a demo user, then
    this function will fail.

    (Exception: if the user is an admin user, then access is *always*
    allowed, and the only check we make is that they're logged in.)

    Arguments:
        admin_required: user must be logged in as a Google Appengine admin
        developer_required: user_data.developer must be True
        moderator_required: user_data.moderator must be True
        demo_user_allowed: user_data.is_demo can be True
        phantom_user_allowed: user_data.is_phantom can be True

    Raises:
        LoginFailedError if any of the necessary conditions are not
        met.  The exception-string gives a reason for the failure.
    """
    user_data = user_models.UserData.current()
    if not user_data:
        raise LoginFailedError("login-required")

    # Admins always have access to everything.
    if users.is_current_user_admin():
        return

    if admin_required and not users.is_current_user_admin():
        raise LoginFailedError("admin-only")

    if developer_required and not user_data.developer:
        raise LoginFailedError("developer-only")

    # Developers are automatically moderators.
    is_moderator = user_data.moderator or user_data.developer
    if moderator_required and not is_moderator:
        raise LoginFailedError("moderator-only")

    if (not demo_user_allowed) and user_data.is_demo:
        return LoginFailedError("no-demo-user")

    if (not phantom_user_allowed) and user_data.is_phantom:
        return LoginFailedError("no-phanthom-user")


def _go_to_login(handler, why):
    """Redirect the user to the login page and log the access attempt."""
    user_data = user_models.UserData.current()
    if user_data:
        logging.warning("Attempt by %s to access %s page"
                        % (user_data.user_id, why))
    # can't import util here because of circular dependencies
    url = "/login?continue=%s" % urllib.quote(handler.request.uri)
    return handler.redirect(url)


def open_access(func):
    """Decorator that allows anyone to access this page."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'open-access'   # for sanity checks
    return wrapper


def manual_access_checking(func):
    """Decorator that documents the func will do its own access checking."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'manual-access'   # checked in RequestHandler
    return wrapper


def login_required_and(func,
                       admin_required=False,
                       developer_required=False,
                       moderator_required=False,
                       demo_user_allowed=False,
                       phantom_user_allowed=True):
    """Decorator that allows (certain) logged-in users to access this page.

    In addition to checking whether the user is logged in, this
    function also checks access based on the *type* of the user:
    if demo_allowed==False, for instance, and the logged-in user
    is a demo user, then access will be denied.

    (Exception: if the user is an admin user, then access is *always*
    allowed, and the only check we make is that they're logged in.)

    The default values specify the default permissions: for instance,
    phantom users are considered a valid user by this routine.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_login(admin_required, developer_required,
                         moderator_required, demo_user_allowed,
                         phantom_user_allowed)
        except LoginFailedError, why:
            return _go_to_login(self, str(why))

        return func(*args, **kwargs)

    # For purposes of IDing this decorator, just store the True arguments.
    all_local_vars = locals()
    arg_names = [var for var in all_local_vars if
                 all_local_vars[var] and
                 var not in ('func', 'wrapper', 'all_arg_names')]
    auth_decorator = 'login-required(%s)' % ','.join(arg_names)
    assert "_access_control" not in wrapper.func_dict, \
           ("Mutiple auth decorators: %s and %s"
            % (wrapper._access_control, auth_decorator))
    wrapper._access_control = auth_decorator   # checked in RequestHandler
    return wrapper


@request_cache.cache()
def is_current_user_demo_user():
    user_data = models.UserData.current()
    return user_data and user_data.is_demo


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
    """Decorator checking that users of a request are register as a developer."""

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
    """Decorator checking that users of a request is registered as a moderator."""

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
    """Decorator checking that users of a request have an admin account."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_admin():
            return method(self, *args, **kwargs)
        else:
            return _go_to_login(self, "admin-only")

    assert "_access_control" not in wrapper.func_dict, "Mutiple auth decorators"
    wrapper._access_control = 'admin-only'   # checked in RequestHandler
    return wrapper

def is_current_user(user_data):
    current_user_data = user_models.UserData.current()
    return (current_user_data and
            current_user_data.user_id == user_data.user_id)


# This isn't an access-control method, but is still useful.
def dev_server_only(method):
    """Decorator that prevents a handler from working in production"""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if app.App.is_dev_server:
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
