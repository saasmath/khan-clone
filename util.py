import auth.cookies
import os
import datetime
import re
import urllib
import request_cache
import logging
from google.appengine.api import users
from google.appengine.ext import db

from asynctools import AsyncMultiTask, QueryTask

from app import App

# Needed for side effects of secondary imports
import nicknames  # @UnusedImport
import facebook_util
from phantom_users.phantom_util import get_phantom_user_id_from_cookies, \
    is_phantom_id

from api.auth.auth_util import current_oauth_map, allow_cookie_based_auth
import uid
import urlparse


def current_req_has_auth_credentials():
    """Determine whether or not the current request has valid credentials."""
    return get_current_user_id_unsafe() is not None


# TODO(benkomalo): kill this method! Clients interested in the current user
# should use user_models.UserData.current() instead, as this may be returning
# invalid user_id values (though if it's non-empty, then we know that the user
# is logged in.)
@request_cache.cache()
def get_current_user_id_unsafe():
    """Get the user_id a new user would get for the current auth credentials.

    Typically, this is the user_id of the current, logged in user. However,
    it's really important to note that it may correspond to a user_id that
    doesn't belong to any user. For example, if third-party
    credentials are provided (e.g. valid Facebook tokens), and we
    resolve them to point to an existing, different user (through e-mail
    e-mail matching or other means), this would return a user_id value
    that's constructed from the Facebook credentials, even though
    the user_id of the current logged in user is something different.

    Returns:
        A string value for the user_id, or None if no valid auth credentials
        are detected in the request.
    """

    user_id = None

    oauth_map = current_oauth_map()
    if oauth_map:
        user_id = _get_current_user_id_from_oauth_map(oauth_map)

    if not user_id and allow_cookie_based_auth():
        user_id = _get_current_user_id_from_cookies_unsafe()

    return user_id


def _get_current_user_id_from_oauth_map(oauth_map):
    return oauth_map.get_user_id()


# get_current_user_from_cookies_unsafe is labeled unsafe because it should
# never be used in our JSONP-enabled API. Clients should do XSRF checks.
def _get_current_user_id_from_cookies_unsafe():
    user = users.get_current_user()

    user_id = None
    if user:  # if we have a google account
        user_id = uid.google_user_id(user)

    if not user_id:
        user_id = auth.cookies.get_user_from_khan_cookies()

    if not user_id:
        user_id = facebook_util.get_current_facebook_user_id_from_cookies()

    # if we don't have a user_id, then it's not facebook or google
    if not user_id:
        user_id = get_phantom_user_id_from_cookies()

    return user_id


def is_phantom_user(user_id):
    return user_id and is_phantom_id(user_id)


def create_login_url(dest_url):
    return "/login?continue=%s" % urllib.quote_plus(dest_url)


def create_mobile_oauth_login_url(dest_url):
    return "/login/mobileoauth?continue=%s" % urllib.quote_plus(dest_url)


def create_post_login_url(dest_url):
    if dest_url.startswith("/postlogin"):
        return dest_url
    else:
        if (dest_url == '/' or
                dest_url == absolute_url('/')):
            return "/postlogin"
        else:
            return "/postlogin?continue=%s" % urllib.quote_plus(dest_url)


def create_logout_url(dest_url):
    # If the user is viewing a profile page (their own or someone else's)
    # or a coaching page (class_profile or students), go to the home page
    # on logout.
    #
    # Even if the profile page is visible publicly, it doesn't seem like
    # staying there is a particular win. And being kicked to the login
    # screen for the coach pages seems a little awkward.
    #
    if re.search(r'/profile\b|/class_profile\b|/students\b', dest_url):
        return "/logout"
    else:
        return "/logout?continue=%s" % urllib.quote_plus(dest_url)


def seconds_since(dt):
    return seconds_between(dt, datetime.datetime.now())


def seconds_between(dt1, dt2):
    timespan = dt2 - dt1
    return float(timespan.seconds + (timespan.days * 24 * 3600))


def minutes_between(dt1, dt2):
    return seconds_between(dt1, dt2) / 60.0


def hours_between(dt1, dt2):
    return seconds_between(dt1, dt2) / (60.0 * 60.0)


def thousands_separated_number(x):
    # See http://stackoverflow.com/questions/1823058/how-to-print-number-with-commas-as-thousands-separators-in-python-2-x
    if x < 0:
        return '-' + thousands_separated_number(-x)
    result = ''
    while x >= 1000:
        x, r = divmod(x, 1000)
        result = ",%03d%s" % (r, result)
    return "%d%s" % (x, result)


def async_queries(queries, limit=100000):

    task_runner = AsyncMultiTask()
    for query in queries:
        task_runner.append(QueryTask(query, limit=limit))
    task_runner.run()

    return task_runner


def config_iterable(plain_config, batch_size=50, limit=1000):

    config = plain_config

    try:
        # This specific use of the QueryOptions private API was
        # suggested to us by the App Engine team.  Wrapping in
        # try/except in case it ever goes away.
        from google.appengine.datastore import datastore_query
        config = datastore_query.QueryOptions(
            config=plain_config,
            limit=limit,
            offset=0,
            prefetch_size=batch_size,
            batch_size=batch_size)

    except Exception, e:
        logging.exception("Failed to create QueryOptions config object: %s", e)

    return config


def _get_url_parts(url):
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    if not netloc:
        # No server_name - must be a relative url.
        if 'HTTP_HOST' in os.environ:
            netloc = os.environ['HTTP_HOST']  # includes port string
        else:
            server_name = os.environ['SERVER_NAME']

            # Note that this is always a string
            port = os.environ['SERVER_PORT']
            if port == "80":
                netloc = server_name
            else:
                netloc = "%s:%s" % (server_name, port)
    return (scheme, netloc, path, query, fragment)


def secure_url(url):
    """ Given a Khan Academy URL (i.e. not to an external site), returns an
    absolute https version of the URL, if possible.

    Abstracts away limitations of https, such as non-support in vanity domains
    and dev servers.

    """

    if url.startswith("https://"):
        return url

    if App.is_dev_server:
        # Dev servers can't handle https.
        return url

    _, netloc, path, query, fragment = _get_url_parts(url)

    if netloc.lower().endswith(".khanacademy.org"):
        # Vanity domains can't handle https - but all the ones we own
        # are simple CNAMEs to the default app engine instance.
        # http://code.google.com/p/googleappengine/issues/detail?id=792
        netloc = "khan-academy.appspot.com"

    return urlparse.urlunsplit(("https", netloc, path, query, fragment))


def insecure_url(url):
    """ Given a Khan Academy URL (i.e. not to an external site), returns an
    absolute http version of the URL.
    
    In dev servers, this always just returns the same URL since dev servers
    never convert to/from secure URL's.

    """

    if url.startswith("http://"):
        return url
    
    if App.is_dev_server:
        # Dev servers can't handle https/http conversion
        return url

    _, netloc, path, query, fragment = _get_url_parts(url)

    if netloc.lower() == "khan-academy.appspot.com":
        # https://khan-academy.appspot.com is the HTTPS equivalent of the
        # default appengine instance
        netloc = "www.khanacademy.org"

    return urlparse.urlunsplit(("http", netloc, path, query, fragment))


def absolute_url(relative_url):
    return 'http://%s%s' % (os.environ['HTTP_HOST'], relative_url)


def static_url(relative_url):
    if (App.is_dev_server or
            not os.environ['HTTP_HOST'].lower().endswith(".khanacademy.org")):
        return relative_url
    else:
        return "http://khan-academy.appspot.com%s" % relative_url


def is_khanacademy_url(url):
    """ Determines whether or not the specified URL points to a Khan Academy
    property.

    Relative URLs are considered safe and owned by Khan Academy.
    """

    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    # Check all absolute URLs
    if (netloc and
            not netloc.endswith(".khanacademy.org") and
            not netloc.endswith(".khan-academy.appspot.com") and
            not netloc == "khan-academy.appspot.com"):
        return False

    # Relative URL's are considered to be a Khan Academy URL.
    return True


def clone_entity(e, **extra_args):
    """http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property
    Clones an entity, adding or overriding constructor attributes.

    The cloned entity will have exactly the same property values as
    the original entity, except where overridden. By default it will
    have no parent entity or key name, unless supplied.
    
    Args:
        e: The entity to clone
        extra_args: Keyword arguments to override from the cloned entity and
        pass to the constructor.
    Returns:
        A cloned, possibly modified, copy of entity e.
    """
    klass = e.__class__
    props = dict((k, v.__get__(e, klass))
                 for k, v in klass.properties().iteritems())
    props.update(extra_args)
    return klass(**props)


def parse_iso8601(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def prefetch_refprops(entities, *props):
    """http://blog.notdot.net/2010/01/ReferenceProperty-prefetching-in-App-Engine
    Loads referenced models defined by the given model properties
    all at once on the given entities.

    Example:
    posts = Post.all().order("-timestamp").fetch(20)
    prefetch_refprop(posts, Post.author)
    """
    # Get a list of (entity,property of this entity)
    fields = [(entity, prop) for entity in entities for prop in props]
    # Pull out an equally sized list of the referenced key for each
    # field (possibly None)
    ref_keys_with_none = [prop.get_value_for_datastore(x)
                          for x, prop in fields]
    # Make a dict of keys:fetched entities
    ref_keys = filter(None, ref_keys_with_none)
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    # Set the fetched entity on the non-None reference properties
    for (entity, prop), ref_key in zip(fields, ref_keys_with_none):
        if ref_key is not None:
            prop.__set__(entity, ref_entities[ref_key])
    return entities


def coalesce(fn, s):
    """Call a function only if the argument is not None"""
    if s is not None:
        return fn(s)
    else:
        return None


def count_with_cursors(query, max_value=None):
    """ Counts the number of items that match a given query, using cursors
    so that it can return a number over 1000.

    USE WITH CARE: should not be done in user-serving requests and can be
    very slow.
    """
    count = 0
    while (count % 1000 == 0 and
             (max_value is None or count < max_value)):
        current_count = len(query.fetch(1000))
        if current_count == 0:
            break

        count += current_count
        if current_count == 1000:
            cursor = query.cursor()
            query.with_cursor(cursor)

    return count


def build_params(dict):
    """ Builds a query string given a dictionary of key/value pairs for the
    query parameters.
    
    Values will be automatically encoded. If a value is None, it is ignored.

    """
    
    return "&".join("%s=%s" % (k, urllib.quote_plus(v))
                    for k, v in dict.iteritems()
                    if v)
