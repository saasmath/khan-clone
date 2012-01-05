import os
import datetime
import urllib
import request_cache
import logging
from google.appengine.api import users
from google.appengine.ext import db

from asynctools import AsyncMultiTask, QueryTask

from app import App

# Needed for side effects of secondary imports
import nicknames #@UnusedImport
import facebook_util
from phantom_users.phantom_util import get_phantom_user_id_from_cookies, \
    is_phantom_id

from api.auth.google_util import get_google_user_id_and_email_from_oauth_map
from api.auth.auth_util import current_oauth_map, allow_cookie_based_auth

@request_cache.cache()
def get_current_user_id():
    user_id = None

    oauth_map = current_oauth_map()
    if oauth_map:
        user_id = get_current_user_id_from_oauth_map(oauth_map)

    if not user_id and allow_cookie_based_auth():
        user_id = get_current_user_id_from_cookies_unsafe()

    return user_id

def get_current_user_id_from_oauth_map(oauth_map):
    user_id = None

    if oauth_map.uses_google():
        user_id = get_google_user_id_and_email_from_oauth_map(oauth_map)[0]
    elif oauth_map.uses_facebook():
        user_id = facebook_util.get_facebook_user_id_from_oauth_map(oauth_map)

    return user_id

# _get_current_user_from_cookies_unsafe is labeled unsafe because it should
# never be used in our JSONP-enabled API. All calling code should just use _get_current_user.
def get_current_user_id_from_cookies_unsafe():
    user = users.get_current_user()

    if user: #if we have a google account
        user_id = "http://googleid.khanacademy.org/" + user.user_id()
    else: #if not a google account, try facebook
        user_id = facebook_util.get_current_facebook_user_id_from_cookies()

    if not user_id: #if we don't have a user_id, then it's not facebook or google
        user_id = get_phantom_user_id_from_cookies()
    return user_id

def is_phantom_user(user_id):
    return user_id and is_phantom_id(user_id)

def create_login_url(dest_url):
    return "/login?continue=%s" % urllib.quote(dest_url)

def create_mobile_oauth_login_url(dest_url):
    return "/login/mobileoauth?continue=%s" % urllib.quote(dest_url)

def create_post_login_url(dest_url):
    if dest_url.startswith("/postlogin"):
        return dest_url
    else:
        return "/postlogin?continue=%s" % urllib.quote(dest_url)

def create_logout_url(dest_url):
    return "/logout?continue=%s" % urllib.quote(dest_url)

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
        # This specific use of the QueryOptions private API was suggested to us by the App Engine team.
        # Wrapping in try/except in case it ever goes away.
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

def absolute_url(relative_url):
    return 'http://%s%s' % (os.environ['HTTP_HOST'], relative_url)

def static_url(relative_url):
    if App.is_dev_server or not os.environ['HTTP_HOST'].lower().endswith(".khanacademy.org"):
        return relative_url
    else:
        return "http://khan-academy.appspot.com%s" % relative_url

def clone_entity(e, **extra_args):
    """http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property
    Clones an entity, adding or overriding constructor attributes.
    
    The cloned entity will have exactly the same property values as the original
    entity, except where overridden. By default it will have no parent entity or
    key name, unless supplied.
    
    Args:
        e: The entity to clone
        extra_args: Keyword arguments to override from the cloned entity and pass
        to the constructor.
    Returns:
        A cloned, possibly modified, copy of entity e.
    """
    klass = e.__class__
    props = dict((k, v.__get__(e, klass)) for k, v in klass.properties().iteritems())
    props.update(extra_args)
    return klass(**props)

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
    # Pull out an equally sized list of the referenced key for each field (possibly None)
    ref_keys_with_none = [prop.get_value_for_datastore(x) for x, prop in fields]
    # Make a dict of keys:fetched entities
    ref_keys = filter(None, ref_keys_with_none)
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    # Set the fetched entity on the non-None reference properties
    for (entity, prop), ref_key in zip(fields, ref_keys_with_none):
        if ref_key is not None:
            prop.__set__(entity, ref_entities[ref_key])
    return entities 
