import sys, os
import logging
from functools import wraps

from app import App
from custom_exceptions import QuietException
from werkzeug.wrappers import BaseResponse

# *PRIVATE* API version number
# Increment the version if any non-public API calls change in a non-backwards compatible way.
# The user will get a message that they need to refresh their HTML. Public API users will not be effected.
XSRF_API_VERSION = "1.0"
XSRF_COOKIE_KEY = "fkey"
XSRF_HEADER_KEY = "HTTP_X_KA_FKEY"

package_dir = os.path.abspath(os.path.join(__file__, "..", "packages"))

# Allow unzipped packages to be imported
# from packages folder
sys.path.insert(0, package_dir)

# Append zip archives to path for zipimport
for filename in os.listdir(package_dir):
    if filename.endswith((".zip", ".egg")):
        sys.path.insert(0, "%s/%s" % (package_dir, filename))

from flask import Flask
from flask import current_app

api_app = Flask('api')
api_app.secret_key = App.flask_secret_key

def route(rule, **options):
    def api_route_wrap(func):
        # Verify that a previous decorator for this function set an
        # authorization policy (we don't want to expose any API on a
        # url without an explicit auth policy for it!)  For this to
        # work, we need that @developer_required/etc be *right after*
        # the last @route decorator for a given function.
        assert '_access_control' in func.func_dict, \
               ('FATAL ERROR: '
                'Need to put an access control decorator '
                '(from api.auth.decorators) on %s.%s. '
                '(It must be the first decorator after all the @route decorators.)'
                % (func.__module__, func.__name__))

        # Send down a common format for all API errors
        func = format_api_errors(func)

        # Allow cross origin requests to our API so our mobile app
        # doesn't have any issues. We rely on OAuth parameters for security,
        # not cross origin policies.
        func = allow_cross_origin(func)

        # Add a header that specifies this response as a Khan API response
        # so client listeners can detect the response if they'd like.
        func = add_api_header(func)

        # Explicitly specify Cache-Control:no-cache unless otherwise specified
        # already. We don't want API responses to be cached.
        func = add_no_cache_header(func)

        rule_desc = rule
        for key in options:
            rule_desc += "[%s=%s]" % (key, options[key])

        # Fix endpoint names for decorated functions by using the rule for names
        api_app.add_url_rule(rule, rule_desc, func, **options)

        return func

    return api_route_wrap

def is_current_api_version(xsrf_token):
    if not xsrf_token:
        return True # Only validate website users

    delims = xsrf_token.split("_")

    # Make sure the very first piece of the XSRF token
    # contains the current API version. The .split() above
    # could return an undefined number of pieces depending
    # on the random token's value.
    if delims[0] != XSRF_API_VERSION:
        logging.warning("Out of date API version detected: %s" % (delims[0]))
        return False

    return True

def add_api_header(func):
    @wraps(func)
    def api_header_added(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, current_app.response_class):
            result.headers["X-KA-API-Response"] = "true"

            # Note that cacheable responses can be cached by shared caches, such
            # as proxies. It would be unwise to cache headers that indicate error
            # conditions, since they are per-user.
            cacheable = result.cache_control.public
            if (not cacheable and 
                    not is_current_api_version(os.environ.get(XSRF_HEADER_KEY))):
                result.headers["X-KA-API-Version-Mismatch"] = "true"

        return result

    return api_header_added

def add_no_cache_header(func):
    @wraps(func)
    def no_cache_header_added(*args, **kwargs):
        result = func(*args, **kwargs)

        if not isinstance(result, BaseResponse):
            result = current_app.response_class(result)

        if hasattr(result, "cache_control"):
            # If this isn't an explicitly cacheable response,
            # never cache any API results. We don't want private caches.
            if not result.cache_control.public:
                result.cache_control.no_cache = True

        return result

    return no_cache_header_added

def allow_cross_origin(func):
    @wraps(func)
    def cross_origin_allowed(*args, **kwargs):
        result = func(*args, **kwargs)

        # Let our mobile apps make API calls from their local files, and rely on oauth for security
        if isinstance(result, current_app.response_class):
            result.headers["Access-Control-Allow-Origin"] = os.environ.get("HTTP_ORIGIN") or "*"
            result.headers["Access-Control-Allow-Credentials"] = "true"

        return result

    return cross_origin_allowed

def format_api_errors(func):
    @wraps(func)
    def api_errors_formatted(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            # If any exception makes it all the way up to the top of an API request,
            # send possibly helpful message down for consumer
            if isinstance(e, QuietException):
                logging.info(e)
            else:
                logging.exception(e)

            return current_app.response_class("API error. %s" % e.message, status=500)

    return api_errors_formatted
