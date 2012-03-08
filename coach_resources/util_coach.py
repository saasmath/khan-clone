import request_handler
import util
from models import UserData
from oauth_provider import oauth
import urllib2, urlparse, cgi
import logging
from app import App

class CoachResourcesRequestHandler(request_handler.RequestHandler):
    def render_jinja2_template(self, template_name, template_values):
        template_values["selected_nav_link"] = "coach"
        request_handler.RequestHandler.render_jinja2_template(self, template_name, template_values)

class ViewCoachResources(CoachResourcesRequestHandler):
    def get(self):
        coach = UserData.current()

        if coach is not None:
            coach_email = coach.email
            is_profile_empty = not coach.has_students()
        else:
            coach_email = None
            is_profile_empty = True

        self.render_jinja2_template('coach_resources/view_resources.html', {
            "selected_id": "coach-resources",
            "coach_email": coach_email,
            "is_profile_empty": is_profile_empty,
        })

class ViewToolkit(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/view_toolkit.html', {
            "selected_id": "toolkit",
        })

class ViewBlog(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/schools_blog.html', {
            "selected_id": "schools-blog",
        })

class ViewDemo(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/view_demo.html', {
            "selected_id": "demo",
        })

class AccessDemo(CoachResourcesRequestHandler):
    def get(self):
        oauth_consumer = oauth.OAuthConsumer(App.khan_demo_consumer_key, App.khan_demo_consumer_secret)

        # First leg of OAuth - request token (skip a server call because we have it)
        request_token = oauth.OAuthToken.from_string(App.khan_demo_request_token)

        # Second leg of OAuth - access_token
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
                oauth_consumer,
                token = request_token,
                http_url = "http://www.khanacademy.org/api/auth/access_token")
        oauth_request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), oauth_consumer, request_token)
        file = urllib2.urlopen(oauth_request.to_url())
        access_token = oauth.OAuthToken.from_string(file.read())

        # Third leg access resource
        full_url = "http://www.khanacademy.org/api/auth/token_to_session?continue=/class_profile?coach_email=khanacademy.demo@gmail.com"
        url = urlparse.urlparse(full_url)
        query_params = cgi.parse_qs(url.query)
        for key in query_params:
            query_params[key] = query_params[key][0]

        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
                oauth_consumer,
                token = access_token,
                http_url = full_url,
                parameters = query_params)
        oauth_request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), oauth_consumer, access_token)

        self.redirect(oauth_request.to_url())

class ViewFAQ(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/schools-faq.html', {})
