from gandalf.cache import GandalfCache
from gandalf.config import current_logged_in_identity

def gandalf(bridge_name):

    if not bridge_name:
        raise Exception("Must include 'bridge_name' parameter")

    gandalf_cache = GandalfCache.get()

    bridge = gandalf_cache.get_bridge_model(bridge_name)

    if not bridge:
        raise Exception("Bridge '%s' does not exist" % bridge_name)

    filters = gandalf_cache.get_filter_models(bridge_name)

    identity = current_logged_in_identity()

    # Currently do not support users with no identity
    if not identity:
        return False

    # A user needs to pass a single whitelist, and pass no blacklists, to pass a bridge
    passes_a_whitelist = False

    for filter in filters:
        if filter.whitelist:
            if filter.filter_class.passes_filter(filter, identity):
                passes_a_whitelist = True
        else:
            if filter.filter_class.passes_filter(filter.context, identity):
                return False

    return passes_a_whitelist

def _identity():
    identity = current_logged_in_identity()

    if not identity:
        return None
    
    if isinstance(identity, db.Model):
        return identity.key()
    else:
        return str(identity)
