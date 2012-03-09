from functools import wraps
from google.appengine.api import memcache
import time

def clamp(min_val, max_val):
    """Ensures wrapped fn's return value is between given min and max bounds"""
    def decorator(func):
        @wraps(func)
        def wrapped(*arg, **kwargs):
            return sorted((min_val, func(*arg, **kwargs), max_val))[1]
        return wrapped
    return decorator

def lock(key=None, timeout=10):
    def decorator(func):
        @wraps(func)
        def wrapped(*arg, **kwargs):
            lock_key = key
            if lock_key is None:
                lock_key = "%s.%s__" % (func.__module__, func.__name__)
              
            lock_key = "__mutex_lock_" + lock_key 
                    
            client = memcache.Client()
            got_lock = False
            try:
                # Make sure the func gets called only one at a time
                while not got_lock:
                    locked = client.gets(lock_key)

                    while locked is None:
                        # Initialize the lock if necessary
                        client.set(lock_key, False)
                        locked = client.gets(lock_key)

                    if not locked:
                        # Lock looks available, try to take it with compare and set (expiration of 10 seconds)
                        got_lock = client.cas(lock_key, True, time=timeout)
                    
                    if not got_lock:
                        # If we didn't get it, wait a bit and try again
                        time.sleep(0.1)
                
                results = func(*arg, **kwargs)

            finally:
                if got_lock:
                    # Release the lock
                    client.set(lock_key, False)

            return results
        return wrapped
    return decorator

