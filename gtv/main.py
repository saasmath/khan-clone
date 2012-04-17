import os

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import WSGIApplication, template

import request_handler
import user_util


class RedirectGTV(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        self.redirect("/gtv/")


class ViewGTV(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        path = os.path.join(os.path.dirname(__file__), "index.html")
        self.response.out.write(template.render(path, {}))

application = WSGIApplication([
    ('/gtv/', ViewGTV),
    ('/gtv', RedirectGTV),
])


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
