#########################################
# Remote_API Authentication configuration.
#
# See google/appengine/ext/remote_api/handler.py for more information.
# For datastore_admin datastore copy, you should set the source appid
# value.  'HTTP_X_APPENGINE_INBOUND_APPID', ['trusted source appid here']
#
remoteapi_CUSTOM_ENVIRONMENT_AUTHENTICATION = (
    'HTTP_X_APPENGINE_INBOUND_APPID', ['khanexercises'])

try:
    # We configure django's version here just to make sure
    # we've got it specified in case a 3rd-party library wants to use it.
    # (gae_mini_profiler and gae_bingo currently use it)
    from google.appengine.dist import use_library
    use_library('django', '1.2')
except ImportError:
    # google.appengine.dist has been removed in GAE's python27, replaced by the
    # "libraries" section of app.yaml
    pass
