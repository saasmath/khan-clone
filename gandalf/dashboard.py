from __future__ import with_statement
import os

from google.appengine.ext.webapp import RequestHandler

class Dashboard(RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), "templates/base.html")

        with open(path) as f:
            html = f.read()

        self.response.out.write(html)
