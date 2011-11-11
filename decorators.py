from functools import wraps

def clamp(min_val, max_val):
    def decorator(func):
        @wraps(func)
        def wrapped(*arg, **kwargs):
            return sorted((min_val, func(*arg, **kwargs), max_val))[1]
        return wrapped
    return decorator
