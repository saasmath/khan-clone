from google.appengine.api import memcache

from gandalf.models import _GandalfBridge, _GandalfFilter

REQUEST_CACHE = {}

def flush_request_cache():
    global REQUEST_CACHE
    REQUEST_CACHE = {}

def init_request_cache_from_memcache():
    global REQUEST_CACHE

    if not REQUEST_CACHE.get("loaded_from_memcache"):
        REQUEST_CACHE[GandalfCache.MEMCACHE_KEY] = memcache.get(GandalfCache.MEMCACHE_KEY)
        REQUEST_CACHE["loaded_from_memcache"] = True

class GandalfCache(object):

    MEMCACHE_KEY = "_gandalf_cache"

    @staticmethod
    def get():
        init_request_cache_from_memcache()

        if not REQUEST_CACHE.get(GandalfCache.MEMCACHE_KEY):
            REQUEST_CACHE[GandalfCache.MEMCACHE_KEY] = GandalfCache.load_from_datastore()

        return REQUEST_CACHE[GandalfCache.MEMCACHE_KEY]

    def __init__(self):
        self.bridge_models = {} # Deserialized bridge models
        self.filter_models = {} # Deserialized filter models

    @staticmethod
    def load_from_datastore():
        gandalf_cache = GandalfCache()

        bridges = _GandalfBridge.all()

        for bridge in bridges:

            key = bridge.key().name()

            gandalf_cache.bridge_models[key] = bridge

            # Ordered so blacklist filters are first
            # Without this ordering the logic breaks
            filters = bridge._gandalffilter_set.order('whitelist').fetch(500)

            gandalf_cache.filter_models[key] = filters

        memcache.set(GandalfCache.MEMCACHE_KEY, gandalf_cache)

        return gandalf_cache

    @staticmethod
    def delete_from_memcache():
        memcache.delete(GandalfCache.MEMCACHE_KEY)
