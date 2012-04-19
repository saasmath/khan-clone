"""
Utilities for handling user accounts.

Among other things, this file provides access-control decorators.
All handlers that derive from request_handler.py's RequestHandler
must decorate their get() and post() methods with one of these
decorators.

Here are the decorators that you can use:

@login_required: the user making the request has to be logged in.  For
   oauth, that means that the oauth token they use has to exist in our
   oauth map.  For cookies-based authentication, it means that there is
   a valid cookie (that could only have been created by a logged-in user).

@developer_required: like login_required, but the logged in user must have
   user_data.developer == True.

@moderator_required: like login_required, but the logged in user must have
   user_data.moderator == True.

@admin_required: like login_required, but the logged in user must be an
   admin.  (We use google's auth for this; users.current_user_is_admin()
   must be true.)

@login_required_and: the above are all special cases of this more generic
   decorator, which can be used when more complex access control is
   required.

@open_access: anyone can access this url, they don't need to be logged in.
   This is used for urls that are not protected (developer-only, say)
   and do not have any user-specific information in them.

@manual_access_checking: anyone can access this url, they don't even
   need a valid oauth credential or cookie.  The expectation is the
   handler will do its own authentication.  Use sparingly!

@dev_server_only: unlike the above, which concern the user,
   this concerns the platform the appengine instance is running on.
   This decorator says a handler is not available in production;
   it can only be used when running a dev_appserver instance.
   It's used for things like importing test data.

The non-decorator routines tell you something about the current user:
   is_current_user_moderator()
   is_current_user_developer()
"""

from functools import wraps
import logging
import urllib

from google.appengine.api import users

from api.auth import xsrf
import app
import request_cache


class LoginFailedError(Exception): pass


def _go_to_login(handler, why):
    """Redirect the user to the login page and log the access attempt."""
    user_data = user_models.UserData.current()
    if user_data:
        logging.warning("Attempt by %s to access %s page"
                        % (user_data.user_id, why))
    # can't import util here because of circular dependencies
    url = "/login?continue=%s" % urllib.quote(handler.request.uri)
    return handler.redirect(url)


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
        raise LoginFailedError("no-demo-user")

    if (not phantom_user_allowed) and user_data.is_phantom:
        raise LoginFailedError("no-phantom-user")


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


def login_required_and(admin_required=False,
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
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                verify_login(admin_required, developer_required,
                             moderator_required, demo_user_allowed,
                             phantom_user_allowed)
            except LoginFailedError, why:
                return _go_to_login(self, str(why))

            # The request we're verifying login for may spawn some API
            # requests.  To make sure those can succeed, we set an xsrf
            # cookie -- the API routines have different authorization code
            # than non-API routines, and need this cookie.
            xsrf.create_xsrf_cookie_if_needed(self)

            return method(self, *args, **kwargs)

        # For purposes of IDing this decorator, just store the True arguments.
        all_local_vars = locals()
        arg_names = [var for var in all_local_vars if
                     all_local_vars[var] and
                     var not in ('method', 'wrapper', 'all_arg_names')]
        auth_wrapper = 'login-required(%s)' % ','.join(arg_names)
        assert "_access_control" not in wrapper.func_dict, \
               ("Mutiple auth decorators: %s and %s"
                % (wrapper._access_control, auth_wrapper))
        wrapper._access_control = auth_wrapper   # checked in RequestHandler
        return wrapper

    return decorator


def admin_required(method):
    return login_required_and(admin_required=True)(method)


def developer_required(method):
    return login_required_and(developer_required=True)(method)


def moderator_required(method):
    return login_required_and(moderator_required=True)(method)


def login_required(method):
    """Verify a user is logged in.  Phantom users are considered logged in."""
    return login_required_and()(method)


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


@request_cache.cache()
def is_current_user_developer():
    user_data = user_models.UserData.current()
    return user_data and (users.is_current_user_admin() or
                          user_data.developer)

@request_cache.cache()
def is_current_user_moderator():
    user_data = user_models.UserData.current()
    return user_data and (users.is_current_user_admin() or
                          user_data.moderator or user_data.developer)


# Put down here to avoid circular-import problems.
# See http://effbot.org/zone/import-confusion.htm
import user_models
