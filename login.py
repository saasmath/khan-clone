import datetime
import logging
import os
import re

from google.appengine.api import mail, users

import auth.cookies
import auth.passwords
import cookie_util
import facebook_util
import request_handler
import shared_jinja
import transaction_util
import uid
import user_models
import user_util
import util

from api import jsonify
from api.auth import auth_util
from api.auth.auth_models import OAuthMap
from app import App
from auth import age_util
from auth.tokens import AuthToken, TransferAuthToken
from counters import user_counter
from models import UserData
from notifications import UserNotifier
from phantom_users.phantom_util import get_phantom_user_id_from_cookies


class Login(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        if self.request_bool("form", default=False):
            self.render_login_form()
        else:
            self.render_login_outer()

    def request_continue_url(self, key="continue", default="/"):
        cont = super(Login, self).request_continue_url(key, default)

        # Always go to /postlogin after a /login, regardless if the continue
        # url actually specified it or not. Important things happen there.
        return util.create_post_login_url(cont)

    def render_login_outer(self):
        """ Renders the login page.

        Note that part of the contents of this page is hosted on an iframe
        and rendered by this same RequestHandler (render_login_form)
        """
        cont = self.request_continue_url()
        direct = self.request_bool('direct', default=False)

        user_data = UserData.current()
        if user_data and not user_data.is_phantom:
            # Don't let users see the login page if they're already logged in.
            # This avoids dangerous edge cases in which users have conflicting
            # Google/FB cookies, and google.appengine.api.users.get_current_user
            # returns a different user than the actual person logged in.
            self.redirect(cont)
            return

        template_values = {
                           'continue': cont,
                           'direct': direct,
                           'google_url': users.create_login_url(cont),
                           }

        self.render_jinja2_template('login.html', template_values)


    def render_login_form(self, identifier=None, errors=None):
        """ Renders the form with the username/password fields. This is
        hosted an in iframe in the main login page.

        errors - a dictionary of possible errors from a previous login that
                 can be highlighted in the UI of the login page
        """
        cont = self.request_continue_url()
        direct = self.request_bool('direct', default=False)

        template_values = {
                           'continue': cont,
                           'direct': direct,
                           'identifier': identifier or "",
                           'errors': errors or {},
                           'google_url': users.create_login_url(cont),
                           }

        self.render_jinja2_template('login_contents.html', template_values)

    @user_util.open_access
    def post(self):
        """ Handles a POST from the login form.

        This happens when the user attempts to login with an identifier (email
        or username) and password.

        """

        cont = self.request_continue_url()

        # Authenticate via username or email + password
        identifier = self.request_string('identifier')
        password = self.request_string('password')
        if not identifier or not password:
            errors = {}
            if not identifier: errors['noemail'] = True
            if not password: errors['nopassword'] = True
            self.render_json({'errors': errors})
            return

        user_data = UserData.get_from_username_or_email(identifier.strip())
        if not user_data or not user_data.validate_password(password):
            errors = {}
            errors['badlogin'] = True
            # TODO(benkomalo): IP-based throttling of failed logins?
            self.render_json({'errors': errors})
            return

        # Successful login
        Login.return_login_json(self, user_data, cont)

    @staticmethod
    def return_login_json(handler, user_data, cont="/"):
        """ Handles a successful login for a user by redirecting them
        to the PostLogin URL with the auth token, which will ultimately set
        the auth cookie for them.

        This level of indirection is needed since the Login/Register handlers
        must accept requests with password strings over https, but the rest
        of the site is not (yet) using https, and therefore must use a
        non-https cookie.

        """

        auth_token = AuthToken.for_user(user_data)
        handler.response.write(jsonify.jsonify({
                    'auth': auth_token.value,
                    'continue': cont
                }, camel_cased=True))

class MobileOAuthLogin(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.render_login_page()

    def render_login_page(self, error=None):
        self.render_jinja2_template('login_mobile_oauth.html', {
            "oauth_map_id": self.request_string("oauth_map_id", default=""),
            "anointed": self.request_bool("an", default=False),
            "view": self.request_string("view", default=""),
            "error": error,
        })

    @user_util.manual_access_checking
    def post(self):
        """ POST submissions are for username/password based logins to
        acquire an OAuth access token.

        """

        identifier = self.request_string('identifier')
        password = self.request_string('password')
        if not identifier or not password:
            self.render_login_page("Please enter your username and password.")
            return

        user_data = UserData.get_from_username_or_email(identifier.strip())
        if not user_data or not user_data.validate_password(password):
            # TODO(benkomalo): IP-based throttling of failed logins?
            self.render_login_page("Your login or password is incorrect.")
            return

        # Successful login - convert to an OAuth access_token
        oauth_map_id = self.request_string("oauth_map_id", default="")
        oauth_map = OAuthMap.get_by_id_safe(oauth_map_id)
        if not oauth_map:
            self.render_login_page("Unable to find OAuthMap by id.")
            return

        # Mint the token and persist to the oauth_map
        oauth_map.khan_auth_token = AuthToken.for_user(user_data).value
        oauth_map.put()

        # Flush the "apply phase" of the above put() to ensure that subsequent
        # retrievals of this OAuthmap returns fresh data. GAE's HRD can
        # otherwise take a second or two to propagate the data, and the
        # following authorize endpoint redirect below could happen quicker
        # than that in some cases.
        oauth_map = OAuthMap.get(oauth_map.key())

        # Need to redirect back to the http authorize endpoint
        return auth_util.authorize_token_redirect(oauth_map, force_http=True)

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
    def _consume_auth_token(self):
        """Checks to see if a valid auth token is specified as a param
        in the request, so it can be converted into a cookie
        and used as the identifier for the current and future requests.
        """

        auth_stamp = self.request_string("auth")
        if auth_stamp:
            # If an auth stamp is provided, it means they logged in using
            # a password via HTTPS, and it has redirected here to postlogin
            # to set the auth cookie from that token. We can't rely on
            # UserData.current() yet since no cookies have yet been set.
            token = AuthToken.for_value(auth_stamp)
            if not token:
                logging.error("Invalid authentication token specified")
            else:
                user_data = UserData.get_from_user_id(token.user_id)
                if not user_data or not token.is_valid(user_data):
                    logging.error("Invalid authentication token specified")
                else:
                    # Good auth stamp - set the cookie for the user, which
                    # will also set it for this request.
                    auth.cookies.set_auth_cookie(self, user_data, token)
                    return True
        return False

    def _finish_and_redirect(self, cont):
        # Always delete phantom user cookies on login
        self.delete_cookie('ureg_id')
        self.redirect(cont)

    @user_util.manual_access_checking
    def get(self):
        cont = self.request_continue_url()

        self._consume_auth_token()

        user_data = UserData.current(create_if_none=True)
        if not user_data:
            # Nobody is logged in - clear any expired Facebook cookies
            # that may be hanging around.
            facebook_util.delete_fb_cookies(self)

            logging.critical(("Missing UserData during PostLogin, " +
                              "with id: %s, cookies: (%s), google user: %s") %
                             (util.get_current_user_id(),
                              os.environ.get('HTTP_COOKIE', ''),
                              users.get_current_user()))
            self._finish_and_redirect(cont)
            return

        first_time = not user_data.last_login

        if user_data.is_facebook_user and not user_data.has_sendable_email():
            # Facebook can give us the user's e-mail if the user granted
            # us permission to see it - try to update existing users with
            # emails, if we don't already have one for them.
            profile = facebook_util.get_profile_from_cookies()
            fb_email = profile and profile.get("email", "")
            if fb_email:
                # We have to be careful - we haven't always asked for emails
                # from facebook users, so getting an e-mail after the fact
                # may result in a collision with an existing Google or Khan
                # account. In those cases, we silently drop the e-mail.
                existing_user = \
                    user_models.UserData.get_from_user_input_email(fb_email)

                if (existing_user and
                        existing_user.user_id != user_data.user_id):
                    logging.error("FB user gave us e-mail and it "
                                  "corresponds to an existing account. "
                                  "Ignoring e-mail value.")
                else:
                    user_data.user_email = fb_email

        # If the user has a public profile, we stop "syncing" their username
        # from Facebook, as they now have an opportunity to set it themself
        if not user_data.username:
            user_data.update_nickname()

        # Set developer and moderator to True if user is admin
        if ((not user_data.developer or not user_data.moderator) and
                users.is_current_user_admin()):
            user_data.developer = True
            user_data.moderator = True

        user_data.last_login = datetime.datetime.utcnow()
        user_data.put()

        complete_signup = self.request_bool("completesignup", default=False)
        if first_time:
            email_now_verified = None
            if user_data.has_sendable_email():
                email_now_verified = user_data.email

                # Look for a matching UnverifiedUser with the same e-mail
                # to see if the user used Google login to verify.
                unverified_user = user_models.UnverifiedUser.get_for_value(
                        email_now_verified)
                if unverified_user:
                    unverified_user.delete()

            # Note that we can only migrate phantom users right now if this
            # login is not going to lead to a "/completesignup" page, which
            # indicates the user has to finish more information in the
            # signup phase.
            if not complete_signup:
                # If user is brand new and has 0 points, migrate data.
                phantom_id = get_phantom_user_id_from_cookies()
                if phantom_id:
                    phantom_data = UserData.get_from_db_key_email(phantom_id)
                    if _upgrade_phantom_into(phantom_data, user_data):
                        cont = "/newaccount?continue=%s" % cont
        if complete_signup:
            cont = "/completesignup"

        self._finish_and_redirect(cont)

class Logout(request_handler.RequestHandler):
    @staticmethod
    def delete_all_identifying_cookies(handler):
        handler.delete_cookie('ureg_id')
        handler.delete_cookie(auth.cookies.AUTH_COOKIE_NAME)

        # Delete session cookie set by flask (used in /api/auth/token_to_session)
        handler.delete_cookie('session')

        # Delete Facebook cookie, which sets ithandler both on "www.ka.org" and ".www.ka.org"
        facebook_util.delete_fb_cookies(handler)

    @user_util.open_access
    def get(self):
        google_user = users.get_current_user()
        Logout.delete_all_identifying_cookies(self)

        next_url = self.request_continue_url()
        if google_user is not None:
            next_url = users.create_logout_url(next_url)
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

class Signup(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        """ Renders the register for new user page.  """

        if (self.request_bool('under13', default=False)
                or cookie_util.get_cookie_value(auth.cookies.U13_COOKIE_NAME)):
            # User detected to be under13. Show them a sorry page.
            name = self.request_string('name', default=None)
            parent_registered = cookie_util.get_cookie_value('u13') == "subscribed"
            self.render_jinja2_template(
                    'under13.html', {
                            'name': name,
                            'parent_registered': parent_registered,
                    })
            return

        template_values = {
            'errors': {},
            'values': {},
            'google_url': users.create_login_url("/postlogin?completesignup=1"),
        }
        self.render_jinja2_template('signup.html', template_values)

    @user_util.manual_access_checking
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

        errors = {}

        # Under-13 check (note the JavaScript on our form should never really
        # send an invalid date, but just to make sure...)
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

            # TODO(benkomalo): investigate how reliable setting cookies from
            # a jQuery POST is going to be
            self.render_json({"under13": True})
            return

        existing_google_user_detected = False
        resend_detected = False

        if values['email']:
            email = values['email']

            # Perform loose validation - we can't actually know if this is
            # valid until we send an e-mail.
            if not _email_re.search(email):
                errors['email'] = "That email appears to be invalid."
            else:
                existing = UserData.get_from_user_input_email(email)
                if existing is not None:
                    if existing.has_password():
                        # TODO(benkomalo): do something nicer and maybe ask the
                        # user to try and login with that e-mail?
                        errors['email'] = "Oops. There's already an account with that e-mail."
                    else:
                        existing_google_user_detected = True
                        logging.warn("User tried to register with password, "
                                     "but has an account w/ Google login")
                else:
                    # No full user account detected, but have they tried to
                    # signup before and still haven't verified their e-mail?
                    existing = user_models.UnverifiedUser.get_for_value(email)
                    resend_detected = existing is not None
        else:
            errors['email'] = "Please enter your email."

        if existing_google_user_detected:
            # TODO(benkomalo): just deny signing up with username/password for
            # existing users with a Google login. In the future, we can show
            # a message to ask them to sign in with their Google login
            errors['email'] = (
                    "There is already an account with that e-mail. " +
                    "If it's yours, sign in with Google below.")

        if len(errors) > 0:
            self.render_json({'errors': errors})
            return

        # Success!
        unverified_user = user_models.UnverifiedUser.get_or_insert_for_value(
                email,
                birthdate)
        Signup.send_verification_email(unverified_user)

        response_json = {
                'success': True,
                'email': email,
                'resend_detected': resend_detected,
                }

        if App.is_dev_server:
            # Send down the verification token so the client can easily
            # create a link to test with.
            response_json['token'] = unverified_user.randstring

        # TODO(benkomalo): since users are now blocked from further access
        #    due to requiring verification of e-mail, we need to do something
        #    about migrating phantom data (we can store the phantom id in
        #    the UnverifiedUser object and migrate after they finish
        #    registering, for example)
        self.render_json(response_json, camel_cased=True)

    @staticmethod
    def send_verification_email(unverified_user):
        recipient = unverified_user.email
        verification_link = CompleteSignup.build_link(unverified_user)

        template_values = {
                'verification_link': verification_link,
            }

        body = shared_jinja.template_to_string(
                'verification-email-text-only.html',
                template_values)

        if not App.is_dev_server:
            mail.send_mail(
                    sender='Khan Academy Accounts <no-reply@khanacademy.org>',
                    to=recipient,
                    subject="Verify your email with Khan Academy",
                    body=body)

class CompleteSignup(request_handler.RequestHandler):
    """ A handler for a page that allows users to create a password to login
    with a Khan Academy account. This is also being doubly used for existing
    Google/FB users to add a password to their account.

    """

    @staticmethod
    def build_link(unverified_user):
        """ Builds a link for an unverified user by using their unique
        randstring as a token embedded into the URL

        """

        return util.absolute_url(
                "/completesignup?token=%s" %
                unverified_user.randstring)

    def resolve_token(self):
        """ Validates the token specified in the request parameters and returns
        a tuple of (token, UnverifiedUser) if it is a valid token.
        Returns (None, None) if no valid token was detected.

        """

        token = self.request_string("token", default=None)
        if not token:
            return (None, None)

        unverified_user = user_models.UnverifiedUser.get_for_token(token)
        if not unverified_user:
            return (None, None)

        # Success - token does indeed point to an unverified user.
        return (token, unverified_user)

    @user_util.manual_access_checking
    def get(self):
        if self.request_bool("form", default=False):
            return self.render_form()
        else:
            return self.render_outer()

    def render_outer(self):
        """ Renders the second part of the user signup step, after the user
        has verified ownership of their e-mail account.

        The request URI must include a valid token from an UnverifiedUser, and
        can be made via build_link(), or be made by a user without an existing
        password set.

        Note that the contents are actually rendered in an iframe so it
        can be sent over https (generated in render_form).

        """
        (valid_token, _) = self.resolve_token()
        user_data = UserData.current()
        if valid_token and user_data:
            if not user_data.is_phantom:
                logging.info("User tried to verify e-mail and complete a " +
                             "signup in a browser with an existing " +
                             "signed-in user. Forcefully signing old user " +
                             "out to avoid conflicts")
                self.redirect(util.create_logout_url(self.request.uri))
                return

            # Ignore phantom users.
            user_data = None

        if not valid_token and not user_data:
            # Just take them to the homepage for now.
            self.redirect("/")
            return

        transfer_token = None
        if user_data:
            if user_data.has_password():
                # The user already has a KA login - redirect them to their profile
                self.redirect(user_data.profile_root)
                return
            elif not user_data.has_sendable_email():
                # This is a case where a Facebook user logged in and tried
                # to signup for a KA password. Unfortunately, since we don't
                # have their e-mail, we can't let them proceed, since, without
                # a valid e-mail we can't reset passwords, etc.
                logging.error("User tried to signup for password with "
                              "no email associated with the account")
                self.redirect("/")
                return
            else:
                # Here we have a valid user, and need to transfer their identity
                # to the inner iframe that will be hosted on https.
                # Since their current cookies may not be transferred/valid in
                # https, mint a custom, short-lived token to transfer identity.
                transfer_token = TransferAuthToken.for_user(user_data).value

        template_values = {
            'params': util.build_params({
                                         'token': valid_token,
                                         'transfer_token': transfer_token,
                                         }),
            'continue': self.request_string("continue", default="/")
        }

        self.render_jinja2_template('completesignup.html', template_values)

    def render_form(self):
        """ Renders the contents of the form for completing a signup. """

        valid_token, unverified_user = self.resolve_token()
        user_data = _resolve_user_in_https_frame(self)
        if not valid_token and not user_data:
            # TODO(benkomalo): handle this better since it's going to be in
            # an iframe! The outer container should do this check for us though.

            # Just take them to the homepage for now.
            self.redirect("/")
            return

        if not valid_token and user_data:
            if user_data.has_password():
                # The user already has a KA login - redirect them to
                # their profile
                self.redirect(user_data.profile_root)
                return
            elif not user_data.has_sendable_email():
                self.redirect("/")
                return

        values = {}
        if valid_token:
            # Give priority to the token in the URL.
            values['email'] = unverified_user.email
            user_data = None
        else:
            # Must be that the user is signing in with Google/FB and wanting
            # to create a KA password to associate with it

            # TODO(benkomalo): handle storage for FB users. Right now their
            # "email" value is a URI like http://facebookid.ka.org/1234
            email = user_data.email
            nickname = user_data.nickname
            if user_data.has_sendable_email():
                values['email'] = email

                if email.split('@')[0] == nickname:
                    # The user's "nickname" property defaults to the user part
                    # of their e-mail. Encourage them to use a real name and
                    # leave the name field blank in that case.
                    nickname = ""

            values['nickname'] = nickname
            values['gender'] = user_data.gender
            values['username'] = user_data.username

        template_values = {
            'user': user_data,
            'values': values,
            'token': valid_token,
        }
        self.render_jinja2_template('completesignup_contents.html', template_values)

    @user_util.manual_access_checking
    def post(self):
        valid_token, unverified_user = self.resolve_token()
        user_data = _resolve_user_in_https_frame(self)
        if not valid_token and not user_data:
            logging.warn("No valid token or user for /completesignup")
            self.redirect("/")
            return

        if valid_token:
            if user_data:
                logging.warn("Existing user is signed in, but also specified "
                             "a valid UnverifiedUser's token. Ignoring "
                             " existing sign-in and using token")
            user_data = None

        # Store values in a dict so we can iterate for monotonous checks.
        values = {
            'nickname': self.request_string('nickname', default=None),
            'gender': self.request_string('gender', default="unspecified"),
            'username': self.request_string('username', default=None),
            'password': self.request_string('password', default=None),
        }

        # Simple existence validations
        errors = {}
        for field, error in [('nickname', "Please tell us your name."),
                             ('username', "Please pick a username."),
                             ('password', "We need a password from you.")]:
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
            if user_models.UniqueUsername.is_username_too_short(username):
                errors['username'] = "Sorry, that username's too short."
            elif not user_models.UniqueUsername.is_valid_username(username):
                errors['username'] = "Usernames must start with a letter and be alphanumeric."

            # Only check to see if it's available if we're changing values
            # or if this is a brand new UserData
            elif ((not user_data or user_data.username != username) and
                    not user_models.UniqueUsername.is_available_username(username)):
                errors['username'] = "That username isn't available."

        if values['password']:
            password = values['password']
            if not auth.passwords.is_sufficient_password(password,
                                                         values['nickname'],
                                                         values['username']):
                errors['password'] = "Sorry, but that password's too weak."


        if len(errors) > 0:
            self.render_json({'errors': errors}, camel_cased=True)
            return

        if user_data:
            # Existing user - update their info
            def txn():
                if (username != user_data.username
                        and not user_data.claim_username(username)):
                    errors['username'] = "That username isn't available."
                    return False

                user_data.set_password(password)
                user_data.update_nickname(values['nickname'])

            transaction_util.ensure_in_transaction(txn, xg_on=True)
            if len(errors) > 0:
                self.render_json({'errors': errors}, camel_cased=True)
                return

        else:
            # Converting unverified_user to a full UserData.
            num_tries = 0
            user_data = None
            while not user_data and num_tries < 2:
                # Double-check to ensure we don't create any duplicate ids!
                user_id = uid.new_user_id()
                user_data = user_models.UserData.insert_for(
                        user_id,
                        unverified_user.email,
                        username,
                        password,
                        birthdate=unverified_user.birthdate,
                        gender=gender)

                if not user_data:
                    self.render_json({'errors': {'username': "That username isn't available."}},
                                     camel_cased=True)
                    return
                elif user_data.username != username:
                    # Something went awry - insert_for may have returned
                    # an existing user due to an ID collision. Try again.
                    user_data = None
                num_tries += 1

            if not user_data:
                logging.error("Tried several times to create a new user " +
                              "unsuccessfully")
                self.render_json({
                        'errors': {'username': "Oops! Something went wrong. " +
                                               "Please try again later."}
                }, camel_cased=True)
                return

            # Nickname is special since it requires updating external indices.
            user_data.update_nickname(values['nickname'])

            # TODO(benkomalo): move this into a transaction with the above creation
            unverified_user.delete()

        # TODO(benkomalo): give some kind of "congrats"/"welcome" notification
        Login.return_login_json(self, user_data, cont=user_data.profile_root)

class PasswordChange(request_handler.RequestHandler):
    """ Handler for changing a user's password.

    This must always be rendered in an https form. If a request is made to
    render the form in HTTP, this handler will automatically redirect to
    the HTTPS version with a transfer_token to identify the user in HTTPS.

    """

    @user_util.manual_access_checking
    def get(self):
        # Always render on https.
        if self.request.scheme != "https" and not App.is_dev_server:
            self.redirect(self.secure_url_with_token(self.request.uri))
            return

        if self.request_bool("success", default=False):
            self.render_form(message="Password changed", success=True)
        else:
            self.render_form()

    def render_form(self, message=None, success=False):
        transfer_token_value = self.request_string("transfer_token", default="")
        self.render_jinja2_template('password-change.html',
                                    {'message': message or "",
                                     'success': success,
                                     'transfer_token': transfer_token_value})

    def secure_url_with_token(self, url):
        user_data = UserData.current()
        if not user_data:
            logging.warn("No user detected for password change")
            return util.secure_url(url)

        token = TransferAuthToken.for_user(user_data).value
        if url.find('?') == -1:
            return "%s?transfer_token=%s" % (util.secure_url(url), token)
        else:
            return "%s&transfer_token=%s" % (util.secure_url(url), token)

    @user_util.manual_access_checking
    def post(self):
        user_data = _resolve_user_in_https_frame(self)
        if not user_data:
            self.response.write("Oops. Something went wrong. Please try again.")
            return

        existing = self.request_string("existing")
        if not user_data.validate_password(existing):
            # TODO(benkomalo): throttle incorrect password attempts
            self.render_form(message="Incorrect password")
            return

        password1 = self.request_string("password1")
        password2 = self.request_string("password2")
        if (not password1 or
                not password2 or
                password1 != password2):
            self.render_form(message="Passwords don't match")
        elif not auth.passwords.is_sufficient_password(password1,
                                                       user_data.nickname,
                                                       user_data.username):
            self.render_form(message="Password too weak")
        else:
            # We're good!
            user_data.set_password(password1)

            # Need to create a new auth token as the existing cookie will expire
            # Use /postlogin to set the cookie. This requires some redirects
            # (/postlogin on http, then back to this pwchange form in https).
            auth_token = AuthToken.for_user(user_data)
            self.redirect("%s?%s" % (
                    util.insecure_url("/postlogin"),
                    util.build_params({
                        'auth': auth_token.value,
                        'continue': self.secure_url_with_token("/pwchange?success=1"),
                    })))

def _resolve_user_in_https_frame(handler):
    """ Determines the current logged in user for the HTTPS request.

    This has logic in additional to UserData.current(), since it should also
    accept TransferAuthTokens, since HTTPS requests may not have normal HTTP
    cookies sent.

    """

    user_data = UserData.current()
    if user_data:
        return user_data

    if not App.is_dev_server and not handler.request.uri.startswith('https'):
        return None

    # On https, users aren't recognized through the normal means of cookie auth
    # since their cookies were set on HTTP domains.
    token_value = handler.request_string("transfer_token", default=None)
    if not token_value:
        return None

    transfer_token = TransferAuthToken.for_value(token_value)
    if not transfer_token:
        return None

    user_data = UserData.get_from_user_id(transfer_token.user_id)
    if user_data and transfer_token.is_valid(user_data):
        return user_data
