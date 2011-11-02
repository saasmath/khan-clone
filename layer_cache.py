import datetime
import logging
import pickle

from google.appengine.api import memcache
from google.appengine.ext import db

import cachepy
from app import App

# layer_cache provides an easy way to cache the result of functions across requests.
# layer_cache uses cachepy's in-memory storage, memcache, and the datastore.
#
# Unless otherwise specified, memcache and in-memory storage are used.
# The datastore layer must be explicitly requested.
#
# When using layer_cache, you can specify which layers to make use of depending on your
# individual use and the need for speed and memory.
#
# _____Explanation by examples:_____
#
# Cache in both memcache and cachepy the result of
# this long-running function using a static key,
# and return the result when available instead of recalculating:
#
# import layer_cache
#
# @layer_cache.cache()
# def calculate_user_averages():
#    ...do lots of long-running work...
#    return result_for_cache
#
#
# and with expiration every minute:
#
# @layer_cache.cache(expiration=60)
# def calculate_user_averages():
#    ...do lots of long-running work...
#    return result_for_cache
#
# Cache using key generated by utility function that
# varies the key based on the function's input parameters:
#
# @layer_cache.cache_with_key_fxn(lambda object: "layer_cache_key_for_object_%s" % object.id())
# def calculate_object_average(object):
#   ... do lots of long-running work...
#   return result_for_cache
#
# _____Manually busting the cache:_____
#
# When you call your cached function, just pass a special "bust_cache"
# named parameter to ignore any existing cached values and replace
# with whatever is newly returned:
#
# calculate_object_average(object, bust_cache=True)
#
# _____Other settings/options:_____
#
# Only cache in datastore:
# @layer_cache.cache(... layer=layer_cache.Layers.Datastore)
#
# Only cache in memcache:
# @layer_cache.cache(... layer=layer_cache.Layers.Memcache)
#
# Only cache in cachepy's in-app memory cache:
# @layer_cache.cache(... layer=layer_cache.Layers.InAppMemory)
#
# Only cache in memcache and datastore:
# @layer_cache.cache(... layer=layer_cache.Layers.Memcache | layer_cache.Layers.Datastore)
#
# Persist the cached values across different uploaded app verions (disabled by default):
# @layer_cache.cache(... persist_across_app_versions=True)
#
# If key has expired or is no longer in the current cache and throws an error when trying to be recomputed, then try getting resource from permanent key that is not set to expire
# @layer_cache.cache(... expiration=60, permanent_cache_key = lambda object: "permanent_layer_cache_key_for_object_%s" % object.id())



DEFAULT_LAYER_CACHE_EXPIRATION_SECONDS = 60 * 60 * 24 * 25 # Expire after 25 days by default

class Layers:
    Datastore = 1
    Memcache = 2
    InAppMemory = 4

def cache(
        expiration = DEFAULT_LAYER_CACHE_EXPIRATION_SECONDS,
        layer = Layers.Memcache | Layers.InAppMemory,
        persist_across_app_versions = False):
    def decorator(target):
        key = "__layer_cache_%s.%s__" % (target.__module__, target.__name__)
        def wrapper(*args, **kwargs):
            return layer_cache_check_set_return(target, lambda *args, **kwargs: key, expiration, layer, persist_across_app_versions, None, *args, **kwargs)
        return wrapper
    return decorator

def cache_with_key_fxn(
        key_fxn,
        expiration = DEFAULT_LAYER_CACHE_EXPIRATION_SECONDS,
        layer = Layers.Memcache | Layers.InAppMemory,
        persist_across_app_versions = False,
        permanent_key_fxn = None):
    def decorator(target):
        def wrapper(*args, **kwargs):
            return layer_cache_check_set_return(target, key_fxn, expiration, layer, persist_across_app_versions, permanent_key_fxn, *args, **kwargs)
        return wrapper
    return decorator

def layer_cache_check_set_return(
        target,
        key_fxn,
        expiration = DEFAULT_LAYER_CACHE_EXPIRATION_SECONDS,
        layer = Layers.Memcache | Layers.InAppMemory,
        persist_across_app_versions = False,
        permanent_key_fxn = None,
        *args,
        **kwargs):

    def get_cached_result(key, namespace, expiration, layer):

        if layer & Layers.InAppMemory:
            result = cachepy.get(key)
            if result is not None:
                return result

        if layer & Layers.Memcache:
            result = memcache.get(key, namespace=namespace)
            if result is not None:
                # Found in memcache, fill upward layers
                if layer & Layers.InAppMemory:
                    cachepy.set(key, result, expiry=expiration)
                return result

        if layer & Layers.Datastore:
            result = KeyValueCache.get(key, namespace=namespace)
            if result is not None:
                # Found in datastore, fill upward layers
                if layer & Layers.InAppMemory:
                    cachepy.set(key, result, expiry=expiration)
                if layer & Layers.Memcache:
                    memcache.set(key, result, time=expiration, namespace=namespace)
                return result

    def set_cached_result(key, namespace, expiration, layer, result):
        # Cache the result
        if layer & Layers.InAppMemory:
            cachepy.set(key, result, expiry=expiration)

        if layer & Layers.Memcache:
            if not memcache.set(key, result, time=expiration, namespace=namespace):
                logging.error("Memcache set failed for %s" % key)

        if layer & Layers.Datastore:
            KeyValueCache.set(key, result, time=expiration, namespace=namespace)


    bust_cache = False
    if "bust_cache" in kwargs:
        bust_cache = kwargs["bust_cache"]
        # delete from kwargs so it's not passed to the target
        del kwargs["bust_cache"]

    key = key_fxn(*args, **kwargs)
    namespace = App.version

    if persist_across_app_versions:
        namespace = None

    if not bust_cache:

        result = get_cached_result(key, namespace, expiration, layer)
        if result is not None:
            return result

    try:
        result = target(*args, **kwargs)

    # an error happened trying to recompute the result, see if there is a value for it in the permanent cache
    except Exception, e:
        import traceback
        traceback.print_exc()

        if permanent_key_fxn is not None:
            permanent_key = permanent_key_fxn(*args, **kwargs)

            result = get_cached_result(permanent_key, namespace, expiration, layer)

            if result is not None:
                logging.info("resource is not available, restoring from permanent cache")

                # In case the key's value has been changed by target's execution
                key = key_fxn(*args, **kwargs)

                #retreived item from permanent cache - save it to the more temporary cache and then return it
                set_cached_result(key, namespace, expiration, layer, result)
                return result

        # could not retrieve item from a permanent cache, raise the error on up
        raise e

    if isinstance(result, UncachedResult):
        # Don't cache this result, just return it
        result = result.result
    else:
        if permanent_key_fxn is not None:
            permanent_key = permanent_key_fxn(*args, **kwargs)
            set_cached_result(permanent_key, namespace, 0, layer, result)

        # In case the key's value has been changed by target's execution
        key = key_fxn(*args, **kwargs)
        set_cached_result(key, namespace, expiration, layer, result)

    return result

# Functions can return an UncachedResult-wrapped object
# to tell layer_cache to skip caching this specific result.
#
# Example:
#
# @layer_cache.cache()
# def slow_and_dangerous():
#   try:
#       return SomethingDangerous()
#   catch:
#       return UncachedResult(SomethingSafe())
#
class UncachedResult():
    def __init__(self, result):
        self.result = result

class KeyValueCache(db.Model):

    value = db.BlobProperty()
    created = db.DateTimeProperty()
    expires = db.DateTimeProperty()

    def is_expired(self):
        return datetime.datetime.now() > self.expires

    @staticmethod
    def get_namespaced_key(key, namespace=""):
        return "%s:%s" % (namespace, key)

    @staticmethod
    def get(key, namespace=""):

        namespaced_key = KeyValueCache.get_namespaced_key(key, namespace)
        key_value = KeyValueCache.get_by_key_name(namespaced_key)

        if key_value and not key_value.is_expired():
            return pickle.loads(key_value.value)

        return None

    @staticmethod
    def set(key, result, time=DEFAULT_LAYER_CACHE_EXPIRATION_SECONDS, namespace=""):

        namespaced_key = KeyValueCache.get_namespaced_key(key, namespace)
        dt = datetime.datetime.now()

        dt_expires = datetime.datetime.max
        if time > 0:
            dt_expires = dt + datetime.timedelta(seconds=time)

        key_value = KeyValueCache.get_or_insert(
                key_name = namespaced_key,
                value = pickle.dumps(result),
                created = dt,
                expires = dt_expires)

        if key_value.created != dt:
            # Already existed, need to overwrite
            key_value.value = pickle.dumps(result)
            key_value.created = dt
            key_value.expires = dt_expires
            key_value.put()

    @staticmethod
    def delete(key, namespace=""):

        namespaced_key = KeyValueCache.get_namespaced_key(key, namespace)
        key_value = KeyValueCache.get_by_key_name(namespaced_key)

        if key_value:
            db.delete(key_value)

