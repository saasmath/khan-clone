from functools import wraps
import logging
import urllib

from google.appengine.api import users

import models
import request_cache
from app import App

def admin_only(method):
    '''Decorator that requires a admin account.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if users.is_current_user_admin():
            return method(self, *args, **kwargs)
        else:
            user_data = models.UserData.current()
            if user_data:
                logging.warning("Attempt by %s to access admin-only page" % user_data.user_id)

            # can't import util here because of circular dependencies
            url = "/login?continue=%s" % urllib.quote(self.request.uri)

            self.redirect(url)
            return

    return wrapper

@request_cache.cache()
def is_current_user_developer():
    user_data = models.UserData.current()
    return bool(users.is_current_user_admin() or (user_data and user_data.developer))

def is_current_user(user_data):
    current_user_data = models.UserData.current()
    return (current_user_data and
            current_user_data.user_id == user_data.user_id)

def developer_only(method):
    '''Decorator that requires a developer account.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_developer():
            return method(self, *args, **kwargs)
        else:
            user_data = models.UserData.current()
            if user_data:
                logging.warning("Attempt by %s to access developer-only page" % user_data.user_id)

            # can't import util here because of circular dependencies
            url = "/login?continue=%s" % urllib.quote(self.request.uri)

            self.redirect(url)
            return

    return wrapper

def dev_server_only(method):
    '''Decorator that prevents a handler from working in production'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if App.is_dev_server:
            return method(self, *args, **kwargs)
        else:
            user_data = models.UserData.current()
            user_id = user_data.user_id or None
            logging.warning(
                "Attempt by %s to access production restricted page" % user_id)

            self.response.clear()
            self.response.set_status(501)  # not implemented
            self.response.set_message = "Method only allowed on dev server"
            return

    return wrapper

@request_cache.cache()
def is_current_user_moderator():
    user_data = models.UserData.current()
    return users.is_current_user_admin() or (user_data and (user_data.moderator or user_data.developer))

def moderator_only(method):
    '''Decorator that requires a moderator account.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_moderator():
            return method(self, *args, **kwargs)
        else:
            user_data = models.UserData.current()
            if user_data:
                logging.warning("Attempt by %s to access moderator-only page" % user_data.user_id)

            # can't import util here because of circular dependencies
            url = "/login?continue=%s" % urllib.quote(self.request.uri)

            self.redirect(url)
            return

    return wrapper
