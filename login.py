from app import App
from counters import user_counter
from google.appengine.api import users
from models import UserData
from notifications import UserNotifier
from phantom_users.phantom_util import get_phantom_user_id_from_cookies

import auth.cookies
import logging
import models
import os
import re
import request_handler
import util

class LoginType():
    """ Enum representing which types of logins a user can use
    to authenticate """
    UNKNOWN = 0
    GOOGLE = 1
    FACEBOOK = 2
    PASSWORD = 3

    @staticmethod
    def is_valid(type_value):
        return (isinstance(type_value, int)
                and type_value >= 1
                and type_value <= 3)

class Login(request_handler.RequestHandler):
    def get(self):
        self.render_login()

    def render_login(self, identifier=None, errors=None):
        """ Renders the login page.

        errors - a dictionary of possible errors from a previous login that
                 can be highlighted in the UI of the login page
        """
        cont = self.request_string('continue', default="/")
        direct = self.request_bool('direct', default=False)

        if App.facebook_app_secret is None:
            self.redirect(users.create_login_url(cont))
            return
        template_values = {
                           'continue': cont,
                           'direct': direct,
                           'identifier': identifier or "",
                           'errors': errors or {},
                           }
        self.render_jinja2_template('login.html', template_values)

    def post(self):
        """ Handles a POST from the login page. """
        cont = self.request_string('continue', default="/")
        login_type = self.request_int('type', default=LoginType.UNKNOWN)
        if not LoginType.is_valid(login_type):
            # Can't figure out what the user wants to do - just send them
            # the login page.
            self.get()
            return

        if login_type == LoginType.FACEBOOK:
            # Unexpected - login through Facebook is done client side using
            # Fb's JS SDK righ tnow.
            logging.error("Unexpected login type of Facebook in Login form")
            return

        if login_type == LoginType.GOOGLE:
            # Redirect to Google's login page
            self.redirect(users.create_login_url(cont))
            return

        elif login_type == LoginType.PASSWORD:
            # Authenticate via username or email + password
            identifier = self.request_string('identifier')
            password = self.request_string('password')
            if not identifier or not password:
                errors = {}
                if not identifier: errors['noemail'] = True
                if not password: errors['nopassword'] = True
                self.render_login(identifier, errors)
                return

            u = models.UserData.get_from_username_or_email(identifier.strip())
            if not u or not u.validate_password(password):
                errors = {}
                errors['badlogin'] = True
                # TODO(benkomalo): IP-based throttling of failed logins?
                self.render_login(identifier, errors)
                return

            auth.cookies.set_auth_cookie(self, u)
            self.redirect(cont)
            return

class MobileOAuthLogin(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('login_mobile_oauth.html', {
            "oauth_map_id": self.request_string("oauth_map_id", default=""),
            "anointed": self.request_bool("an", default=False),
            "view": self.request_string("view", default="")
        })

class PostLogin(request_handler.RequestHandler):
    def get(self):
        cont = self.request_string('continue', default="/")

        # Immediately after login we make sure this user has a UserData entity
        user_data = UserData.current()
        if user_data:

            # Update email address if it has changed
            current_google_user = users.get_current_user()
            if current_google_user and current_google_user.email() != user_data.email:
                user_data.user_email = current_google_user.email()
                user_data.put()

            # If the user has a public profile, we stop "syncing" their username
            # from Facebook, as they now have an opportunity to set it themself
            if not user_data.username:
                user_data.update_nickname()

            # Set developer and moderator to True if user is admin
            if (not user_data.developer or not user_data.moderator) and users.is_current_user_admin():
                user_data.developer = True
                user_data.moderator = True
                user_data.put()

            # If user is brand new and has 0 points, migrate data
            phantom_id = get_phantom_user_id_from_cookies()
            if phantom_id:
                phantom_data = UserData.get_from_db_key_email(phantom_id)

                # First make sure user has 0 points and phantom user has some activity
                if user_data.points == 0 and phantom_data and phantom_data.points > 0:

                    # Make sure user has no students
                    if not user_data.has_students():

                        # Clear all "login" notifications
                        UserNotifier.clear_all(phantom_data)

                        # Update phantom user_data to real user_data
                        phantom_data.user_id = user_data.user_id
                        phantom_data.current_user = user_data.current_user
                        phantom_data.user_email = user_data.user_email
                        phantom_data.user_nickname = user_data.user_nickname

                        if phantom_data.put():
                            # Phantom user was just transitioned to real user
                            user_counter.add(1)
                            user_data.delete()

                        cont = "/newaccount?continue=%s" % cont
        else:

            # If nobody is logged in, clear any expired Facebook cookie that may be hanging around.
            if App.facebook_app_id:
                self.delete_cookie("fbsr_" + App.facebook_app_id)
                self.delete_cookie("fbs_" + App.facebook_app_id)

            logging.critical("Missing UserData during PostLogin, with id: %s, cookies: (%s), google user: %s" % (
                    util.get_current_user_id(), os.environ.get('HTTP_COOKIE', ''), users.get_current_user()
                )
            )

        # Always delete phantom user cookies on login
        self.delete_cookie('ureg_id')

        self.redirect(cont)

class Logout(request_handler.RequestHandler):
    def get(self):
        self.delete_cookie('ureg_id')
        self.delete_cookie(auth.cookies.AUTH_COOKIE_NAME)

        # Delete Facebook cookie, which sets itself both on "www.ka.org" and ".www.ka.org"
        if App.facebook_app_id:
            self.delete_cookie_including_dot_domain('fbsr_' + App.facebook_app_id)
            self.delete_cookie_including_dot_domain('fbm_' + App.facebook_app_id)

        self.redirect(users.create_logout_url(self.request_string("continue", default="/")))

# TODO(benkomalo): move this to a more appropriate, generic spot
# Loose regex for Email validation, copied from django.core.validators
# Most regex or validation libraries are overly strict - this is intentionally
# loose since the RFC is crazy and the only good way to know if an e-mail is
# really valid is to send and see if it fails.
_email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)  # domain

class Register(request_handler.RequestHandler):
    def get(self):
        """ Renders the register for new user page.  """
        cont = self.request_string('continue', default="/")

        template_values = {
            'continue': cont,
            'errors': {},
            'values': {},
        }
        self.render_jinja2_template('register.html', template_values)

    def post(self):
        """ Handles registration request on our site.
        
        Note that new users can still be created via PostLogin if the user
        signs in via Google/FB for the first time - this is for the
        explicit registration via our own services.
        """

        cont = self.request_string('continue', default="/")

        # Store values in a dict so we can iterate for monotonous checks.
        values = {
            'nickname': self.request_string('nickname', default=None),
            'gender': self.request_string('gender', default="unspecified"),
            'birthdate': self.request_string('birthdate', default=None),

            'username': self.request_string('username', default=None),
            'email': self.request_string('email', default=None),
            'password': self.request_string('password', default=None),
        }

        # Simple existence validations
        errors = {}
        for field, error in [('nickname', "Name required"),
                             ('birthdate', "Birthday required"),
                             ('username', "Username required"),
                             ('email', "Email required"),
                             ('password', "Password required")]:
            if not values[field]:
                errors[field] = error

        # Check validity of auth credentials
        if values['email']:
            email = values['email']

            # Perform loose validation - we can't actually know if this is
            # valid until we send an e-mail.
            if not _email_re.search(email):
                errors['email'] = "Email appears to be invalid"

        if values['username']:
            username = values['username']
            # TODO(benkomalo): ask for advice on text
            if not models.UniqueUsername.is_valid_username(username):
                errors['username'] = "Must start with a letter, be alphanumeric, and at least 3 characters"
            elif not models.UniqueUsername.is_available_username(username):
                errors['username'] = "Username is not available"

        if values['password']:
            # TODO(benkomalo): enforce a minimum password quality/length
            pass

        if len(errors) > 0:
            # Never send back down the password.
            del values['password']

            template_values = {
	            'cont': cont,
	            'errors': errors,
	            'values': values,
	        }

            self.render_jinja2_template('register.html', template_values)
            return

        # TODO(benkomalo): actually handle registration
        self.response.write("Not handled yet!")
