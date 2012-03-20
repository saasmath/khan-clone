from app import App
from auth import age_util
from counters import user_counter
from google.appengine.api import users
from models import UserData
from notifications import UserNotifier
from phantom_users.phantom_util import get_phantom_user_id_from_cookies

import auth.cookies
import auth.passwords
import auth.tokens
import cookie_util
import datetime
import logging
import models
import os
import re
import request_handler
import util
import urllib

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
        cont = self.request_continue_url()
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
        cont = self.request_continue_url()
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

            user_data = models.UserData.get_from_username_or_email(identifier.strip())
            if not user_data or not user_data.validate_password(password):
                errors = {}
                errors['badlogin'] = True
                # TODO(benkomalo): IP-based throttling of failed logins?
                self.render_login(identifier, errors)
                return

            # Successful login
            Login.redirect_with_auth_stamp(self, user_data, cont)

    @staticmethod
    def redirect_to_unverified_warning(handler,
                                       unverified_user,
                                       existing_google_user_detected=None):
        """ Handles a successful login for a user that has not had their
        e-mail address verified, and therefore needs to be stopped from
        actually getting an auth token. """
        
        if existing_google_user_detected == None:
            # Check to see if there is an existing UserData account that was
            # created using a Google login.
            existing_google_user_detected = False
            for u in models.UserData.get_all_for_user_input_email(unverified_user.email):
                if not u.has_password():
                    existing_google_user_detected = True
                    break

        handler.redirect("/unverified?token=%s&google=%s" % (
                auth.tokens.EmailVerificationToken.for_user(unverified_user).value,
                "1" if existing_google_user_detected else "0"))

    @staticmethod
    def redirect_with_auth_stamp(handler, user_data, cont="/"):
        """ Handles a successful login for a user by redirecting them
        to the PostLogin URL with the auth token, which will ultimately set
        the auth cookie for them.

        This level of indirection is needed since the Login/Register handlers
        must accept requests with password strings over https, but the rest
        of the site is not (yet) using https, and therefore must use a
        non-https cookie.

        """

        auth_token = auth.tokens.AuthToken.for_user(user_data)
        cont = util.create_post_login_url(cont) + ("&auth=%s" % auth_token)
        cont = util.insecure_url(cont)
        handler.redirect(cont)

class MobileOAuthLogin(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('login_mobile_oauth.html', {
            "oauth_map_id": self.request_string("oauth_map_id", default=""),
            "anointed": self.request_bool("an", default=False),
            "view": self.request_string("view", default="")
        })

def _upgrade_phantom_into(phantom_data, target_data):
    """ Attempts to merge a phantom user into a target user.
    Will bail if any signs that the target user has previous activity.
    """


    # First make sure user has 0 points and phantom user has some activity
    if (phantom_data and phantom_data.points > 0):
        if phantom_data.consume_identity(target_data):
            # Phantom user just converted into a real user.
            user_counter.add(1)

            # Clear all "login" notifications
            UserNotifier.clear_all(phantom_data)
            return True
    return False

class PostLogin(request_handler.RequestHandler):
    def get(self):
        cont = self.request_continue_url()

        auth_stamp = self.request_string("auth")
        if auth_stamp:
            # If an auth stamp is provided, it means they logged in using
            # a password via HTTPS, and it has redirected here to postlogin
            # to set the auth cookie from that token. We can't rely on
            # UserData.current() yet since no cookies have yet been set.
            token = auth.tokens.AuthToken.for_value(auth_stamp)
            if not token:
                logging.error("Invalid authentication token specified")
            else:
                user_data = UserData.get_from_user_id(token.user_id)
                if not user_data or not token.is_valid(user_data):
                    logging.error("Invalid authentication token specified")
                    user_data = None
                else:
                    # Good auth stamp - set the cookie for the user, which
                    # will also set it for this request.
                    auth.cookies.set_auth_cookie(self, user_data, token)
                    
        user_data = UserData.current()
        if user_data:

            # Update email address if it has changed
            current_google_user = users.get_current_user()
            if current_google_user:
                if current_google_user.email() != user_data.email:
                    user_data.user_email = current_google_user.email()
                    user_data.put()
                # TODO(benkomalo): if they have a password based login with
                # matching e-mail, merge the two userdata profiles, since it
                # must be the case that this is the first time logging in
                # with the Google Account.
                
            # If the user has a public profile, we stop "syncing" their username
            # from Facebook, as they now have an opportunity to set it themself
            if not user_data.username:
                user_data.update_nickname()

            # Set developer and moderator to True if user is admin
            if ((not user_data.developer or not user_data.moderator)
                    and users.is_current_user_admin()):
                user_data.developer = True
                user_data.moderator = True
                user_data.put()

            # If user is brand new and has 0 points, migrate data.
            # This should only happen for Facebook/Google users right now,
            # since users with username/password go through the /register
            # code path, which does the merging there.
            phantom_id = get_phantom_user_id_from_cookies()
            if phantom_id:
                phantom_data = UserData.get_from_db_key_email(phantom_id)
                if _upgrade_phantom_into(phantom_data, user_data):
                    cont = "/newaccount?continue=%s" % cont
        else:

            # If nobody is logged in, clear any expired Facebook cookie that may be hanging around.
            if App.facebook_app_id:
                self.delete_cookie("fbsr_" + App.facebook_app_id)
                self.delete_cookie("fbm_" + App.facebook_app_id)

            logging.critical("Missing UserData during PostLogin, with id: %s, cookies: (%s), google user: %s" % (
                    util.get_current_user_id(), os.environ.get('HTTP_COOKIE', ''), users.get_current_user()
                )
            )

        # Always delete phantom user cookies on login
        self.delete_cookie('ureg_id')
        self.redirect(cont)

class Logout(request_handler.RequestHandler):
    @staticmethod
    def delete_all_identifying_cookies(handler):
        handler.delete_cookie('ureg_id')
        handler.delete_cookie(auth.cookies.AUTH_COOKIE_NAME)

        # Delete session cookie set by flask (used in /api/auth/token_to_session)
        handler.delete_cookie('session')

        # Delete Facebook cookie, which sets ithandler both on "www.ka.org" and ".www.ka.org"
        if App.facebook_app_id:
            handler.delete_cookie_including_dot_domain('fbsr_' + App.facebook_app_id)
            handler.delete_cookie_including_dot_domain('fbm_' + App.facebook_app_id)

    def get(self):
        google_user = users.get_current_user()
        Logout.delete_all_identifying_cookies(self)

        next_url = "/"
        if google_user is not None:
            next_url = users.create_logout_url(self.request_continue_url())
        self.redirect(next_url)

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

        if (self.request_bool('under13', default=False)
                or cookie_util.get_cookie_value(auth.cookies.U13_COOKIE_NAME)):
            # User detected to be under13. Show them a sorry page.
            name = self.request_string('name', default=None)
            self.render_jinja2_template('under13.html', {'name': name})
            return

        template_values = {
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

        values = {
            'birthdate': self.request_string('birthdate', default=None),
            'email': self.request_string('email', default=None),
        }

        # Simple existence validations
        errors = {}

        # Under-13 check.
        birthdate = None
        if values['birthdate']:
            try:
                birthdate = datetime.datetime.strptime(values['birthdate'],
                                                       '%Y-%m-%d')
                birthdate = birthdate.date()
            except ValueError:
                errors['birthdate'] = "Invalid birthdate"
        else:
            errors['birthdate'] = "Birthdate required"

        if birthdate and age_util.get_age(birthdate) < 13:
            # We don't yet allow under13 users. We need to lock them out now,
            # unfortunately. Set an under-13 cookie so they can't try again.
            Logout.delete_all_identifying_cookies(self)
            auth.cookies.set_under13_cookie(self)
            self.redirect("/register?under13=1&name=%s" %
                          urllib.quote(values['nickname'] or ""))
            return

        existing_google_user_detected = False
        if values['email']:
            email = values['email']

            # Perform loose validation - we can't actually know if this is
            # valid until we send an e-mail.
            if not _email_re.search(email):
                errors['email'] = "Email appears to be invalid"
            else:
                existing = models.UserData.get_from_user_input_email(email)
                if existing is not None:
                    if existing.has_password():
                        # TODO(benkomalo): do something nicer and maybe ask the
                        # user to try and login with that e-mail?
                        errors['email'] = "There is already an account with that e-mail"
                    else:
                        existing_google_user_detected = True
                        logging.warn("User tried to register with password, "
                                     "but has an account w/ Google login")
                else:
                    # No full user account detected, but have they tried to
                    # signup before and still haven't verified their e-mail?
                    existing = models.UnverifiedUser.get_for_value(email)
                    if existing is not None:
                        # TODO(benkomalo): do something nicer here and present
                        # call to action for re-sending verification e-mail
                        errors['email'] = "Looks like you've already tried signing up"
        else:
            errors['email'] = "Email required"
            
        if len(errors) > 0:
            template_values = {
                'errors': errors,
                'values': values,
            }

            self.render_jinja2_template('register.html', template_values)
            return
        
        # Success!
        unverified_user = models.UnverifiedUser.insert_for(email)

        # TODO(benkomalo): send verification e-mail
        # TODO(benkomalo): since users are now blocked from further access
        #    due to requiring verification of e-mail, we need to do something
        #    about migrating phantom data.

        Login.redirect_to_unverified_warning(self,
                                             unverified_user,
                                             existing_google_user_detected)
        
class CompleteSignup(request_handler.RequestHandler):
    @staticmethod
    def build_link(unverified_user):
        return util.absolute_url(
                "/completesignup?token=%s" %
                auth.tokens.EmailVerificationToken.for_user(unverified_user).value)
        
    def validated_token(self):
        token_value = self.request_string("token", default=None)
        token = auth.tokens.EmailVerificationToken.for_value(token_value)
        
        if not token:
            self.response.bad_request("Invalid parameters")
            return None

        unverified_user = models.UnverifiedUser.get_for_value(token.email)
        if not unverified_user or not token.is_valid(unverified_user):
            self.response.bad_request("Invalid parameters")
            return None

        # Success - token does indeed point to an unverified user.
        return token

    def get(self):
        """ Renders the second part of the user signup step, after the user
        has verified ownership of their e-mail account.

        The request URI must include a valid EmailVerificationToken, and
        can be made via build_link().

        """
        valid_token = self.validated_token()
        if not valid_token:
            # TODO(benkomalo): do something nicer
            self.response.bad_request("Bad token")
            return

        template_values = {
            'errors': {},
            'values': {},
            'token': valid_token,
        }
        self.render_jinja2_template('completesignup.html', template_values)

    def post(self):
        valid_token = self.validated_token()
        if not valid_token:
            # TODO(benkomalo): do something nicer
            self.response.bad_request("Bad token")
            return

        # Store values in a dict so we can iterate for monotonous checks.
        values = {
            'nickname': self.request_string('nickname', default=None),
            'gender': self.request_string('gender', default="unspecified"),
            'username': self.request_string('username', default=None),
            'password': self.request_string('password', default=None),
        }

        # Simple existence validations
        errors = {}
        for field, error in [('nickname', "Name required"),
                             ('username', "Username required"),
                             ('password', "Password required")]:
            if not values[field]:
                errors[field] = error

        gender = None
        if values['gender']:
            gender = values['gender'].lower()
            if gender not in ['male', 'female']:
                gender = None

        if values['username']:
            username = values['username']
            # TODO(benkomalo): ask for advice on text
            if not models.UniqueUsername.is_valid_username(username):
                errors['username'] = "Must start with a letter, be alphanumeric, and at least 3 characters"
            elif not models.UniqueUsername.is_available_username(username):
                errors['username'] = "Username is not available"

        if values['password']:
            password = values['password']
            if not auth.passwords.is_sufficient_password(password,
                                                         values['nickname'],
                                                         values['username']):
                errors['password'] = "Password is too weak"


        if len(errors) > 0:
            # Never send back down the password.
            del values['password']

            template_values = {
                'errors': errors,
                'values': values,
                'token': valid_token,
            }

            self.render_jinja2_template('completesignup.html', template_values)
            return

        unverified_user = models.UnverifiedUser.get_for_value(valid_token.email)

        # TODO(benkomalo): actually move out user id generation to a nice,
        # centralized place and do a double check ID collisions
        import uuid
        user_id = "http://id.khanacademy.org/" + uuid.uuid4().hex
        created_user = models.UserData.insert_for(
                user_id,
                unverified_user.email,
                username,
                password,
                birthdate=unverified_user.birthdate,
                gender=gender)
        
        if not created_user:
            # TODO(benkomalo): STOPSHIP handle the low probability event that a
            # username was taken just as this method was processing.
            self.response.write("Oops. can't make user")
            return
        
        # Nickname is special since it requires updating external indices.
        created_user.update_nickname(values['nickname'])

        # TODO(benkomalo): move this into a transaction with the above creation
        unverified_user.delete()
        
        # TODO(benkomalo): give some kind of "congrats"/"welcome" notification
        Login.redirect_with_auth_stamp(self, created_user)

class PasswordChange(request_handler.RequestHandler):
    def post(self):
        user_data = models.UserData.current()
        if not user_data:
            self.response.unauthorized()
            return

        existing = self.request_string("existing")
        if not user_data.validate_password(existing):
            self.response.unauthorized()
            return

        password1 = self.request_string("password1")
        password2 = self.request_string("password2")
        if not password1 or not password2:
            self.response.bad_request()
            return

        # TODO(benkomalo): actually wire this up to a UI instead of just
        # writing text like this.
        if password1 != password2:
            self.response.write("Passwords don't match.")
        elif not auth.passwords.is_sufficient_password(password1,
                                                       user_data.nickname,
                                                       user_data.username):
            self.response.write("Password too weak.")
        else:
            # We're good!
            user_data.set_password(password1)
            cont = self.request_continue_url()

            # Need to create a new auth token as the existing cookie will expire
            Login.redirect_with_auth_stamp(self, user_data, cont)

class UnverifiedAccount(request_handler.RequestHandler):
    def get(self):
        token_value = self.request_string("token", default="")
        token = auth.tokens.EmailVerificationToken.for_value(token_value)
        # On bad requests, just throw the user back to the homepage.
        if not token:
            self.redirect("/")
            return
        
        unverified_user = models.UnverifiedUser.get_for_value(token.email)
        if not unverified_user or not token.is_valid(unverified_user):
            self.redirect("/")
            return

        # TODO(benkomalo): actually do something different for users with
        #     an existing Google account detected.
        existing_google_user_detected = False
        
        # TODO(benkomalo): STOPSHIP this link should be e-mailed to the user
        # and not actually embedded in this template
        link = CompleteSignup.build_link(unverified_user)
        self.render_jinja2_template(
                'unverified_account.html',
                {
                    'existing_google_user_detected': existing_google_user_detected,
                    'link': link,
                })
