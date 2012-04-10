import os

try:
    import secrets
except:
    class secrets(object):
        pass


# A singleton shared across requests
class App(object):
    # This gets reset every time a new version is deployed on
    # a live server.  It has the form major.minor where major
    # is the version specified in app.yaml and minor auto-generated
    # during the deployment process.  Minor is always 1 on a dev
    # server.
    version = os.environ.get('CURRENT_VERSION_ID')
    root = os.path.dirname(__file__)
    is_dev_server = os.environ["SERVER_SOFTWARE"].startswith('Development')

    offline_mode = False

for attr in [
    'facebook_app_id',
    'facebook_app_secret',
    'google_consumer_key',
    'google_consumer_secret',
    'remote_api_secret',
    'constant_contact_api_key',
    'constant_contact_username',
    'constant_contact_password',
    'flask_secret_key',
    'dashboard_secret',
    'khanbugz_passwd',
    'paypal_token_id',
    'token_recipe_key',
    'khan_demo_consumer_key',
    'khan_demo_consumer_secret',
    'khan_demo_request_token',
]:
    # These secrets are optional in development but not in production
    if App.is_dev_server and not hasattr(secrets, attr):
        setattr(App, attr, None)
    else:
        setattr(App, attr, getattr(secrets, attr))

if App.is_dev_server and App.token_recipe_key is None:
    # If a key is missing to dishout auth tokens on dev, we can't login with
    # our own auth system. So just set it to a random string.
    App.token_recipe_key = 'lkj9Hg7823afpEOI3nmlkfl3jfnklsfQQ'
