import logging
import hashlib
import zlib
from base64 import b64encode, b64decode
from pickle import dumps, loads
from functools import wraps

from flask import request
from flask import current_app
import api.jsonify as apijsonify

from app import App
import datetime
import time

def etag(func_tag_content):
    def etag_wrapper(func):
        @wraps(func)
        def etag_enabled(*args, **kwargs):

            etag_inner_content = "%s:%s" % (func_tag_content(), App.version)
            etag_server = "\"%s\"" % hashlib.md5(etag_inner_content).hexdigest()

            etag_client = request.headers.get("If-None-Match")
            if etag_client and etag_client == etag_server:
                return current_app.response_class(status=304)
            
            result = func(*args, **kwargs)

            if isinstance(result, current_app.response_class):
                result.headers["ETag"] = etag_server
                return result
            else:
                return current_app.response_class(result, headers={"Etag": etag_server})
        return etag_enabled
    return etag_wrapper

_TWO_MONTHS = 60 * 60 * 24 * 60
def cacheable(caching_age=_TWO_MONTHS, cache_token="v"):
    def cacheable_wrapper(func):
        @wraps(func)
        def caching_enabled(*args, **kwargs):
            
            timestamp = request.values.get(cache_token)
            if timestamp is None:
                return func(*args, **kwargs)
            
            result = func(*args, **kwargs)
            if isinstance(result, current_app.response_class):
                result.cache_control.max_age = caching_age
                result.cache_control.public = True
                result.headers['Expires'] = (datetime.datetime.utcnow() +
                                             datetime.timedelta(seconds=caching_age))
                return result
            else:
                return current_app.response_class(result, headers={
                        "Cache-control": ("public, max-age=%s" % caching_age),
                        })
        return caching_enabled
    return cacheable_wrapper

def jsonify(func):
    @wraps(func)
    def jsonified(*args, **kwargs):
        obj = func(*args, **kwargs)

        if isinstance(obj, current_app.response_class):
            return obj

        return obj if type(obj) == str else apijsonify.jsonify(obj)
    return jsonified

def jsonp(func):
    @wraps(func)
    def jsonp_enabled(*args, **kwargs):
        val = func(*args, **kwargs)

        if isinstance(val, current_app.response_class):
            return val

        callback = request.values.get("callback")
        if callback:
            val = "%s(%s)" % (callback, val)
        return current_app.response_class(val, mimetype="application/json")
    return jsonp_enabled

def compress(func):
    @wraps(func)
    def compressed(*args, **kwargs):
        return zlib.compress(func(*args, **kwargs).encode('utf-8'))
    return compressed

def decompress(func):
    @wraps(func)
    def decompressed(*args, **kwargs):
        return zlib.decompress(func(*args, **kwargs)).decode('utf-8')
    return decompressed

def pickle(func):
    @wraps(func)
    def pickled(*args, **kwargs):
        return dumps(func(*args, **kwargs))
    return pickled

def unpickle(func):
    @wraps(func)
    def unpickled(*args, **kwargs):
        return loads(func(*args, **kwargs))
    return unpickled

def base64_encode(func):
    @wraps(func)
    def base64_encoded(*args, **kwargs):
        return b64encode(func(*args, **kwargs))
    return base64_encoded

def base64_decode(func):
    @wraps(func)
    def base64_decoded(*args, **kwargs):
        return b64decode(func(*args, **kwargs))
    return base64_decoded
