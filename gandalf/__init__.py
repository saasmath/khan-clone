import hashlib

from google.appengine.ext import db

from gandalf.models import _GandalfBridge, _GandalfFilter
from gandalf.config import current_logged_in_identity
from gandalf.cache import GandalfCache

def gandalf(bridge_name):

    if not bridge_name:
        raise Exception("Must include 'bridge_name' parameter")

    gandalf_cache = GandalfCache.get()

    bridge = gandalf_cache.bridge_models[bridge_name]

    if not bridge:
        raise Exception("Bridge '%s' does not exist" % bridge_name)

    filters = gandalf_cache.filter_models[bridge_name]

    user_data = current_logged_in_identity()

    # Currently do not support users with no identity
    if not user_data:
        return False

    # A user needs to pass a single whitelist, and pass no blacklists, to pass a bridge
    is_whitelisted = False

    for filter in filters:
        if not filter.whitelist:
            if filter.filter_class.passes(filter.context, user_data):
                return False
        else:
            if filter.filter_class.passes(filter.context, user_data):
                if in_percentage(bridge_name, filter.percentage):
                    return True

    return False

def identity():
    user_data = current_logged_in_identity()

    if not user_data:
        return None

    if isinstance(user_data, db.Model):
        return user_data.key()
    else:
        return str(user_data)

def in_percentage(bridge_name, percentage):

    sig = hashlib.md5(bridge_name + str(identity())).hexdigest()
    sig_num = int(sig, base=16)
    
    return percentage > (sig_num % 100)
