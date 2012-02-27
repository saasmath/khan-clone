from app import App
from counters import user_counter
from google.appengine.api import users
from models import UserData
from notifications import UserNotifier
from phantom_users.phantom_util import get_phantom_user_id_from_cookies
import logging
import os
import request_handler
import util

class Login(request_handler.RequestHandler):
    def get(self):
        """ Renders the login page. """
        cont = self.request_string('continue', default="/")
        direct = self.request_bool('direct', default=False)

        if App.facebook_app_secret is None:
            self.redirect(users.create_login_url(cont))
            return
        template_values = {
                           'continue': cont,
                           'direct': direct
                           }
        self.render_jinja2_template('login.html', template_values)

    def post(self):
        """ Handles a POST from the login page.
        Right now this basically means the user opted to login via Google,
        so redirect them to the appropriate Google Login page.
        """
        cont = self.request_string('continue', default="/")
        self.redirect(users.create_login_url(cont))

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

        # Delete Facebook cookie, which sets itself both on "www.ka.org" and ".www.ka.org"
        if App.facebook_app_id:
            self.delete_cookie_including_dot_domain('fbsr_' + App.facebook_app_id)
            self.delete_cookie_including_dot_domain('fbm_' + App.facebook_app_id)

        self.redirect(users.create_logout_url(self.request_string("continue", default="/")))

