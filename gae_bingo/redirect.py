from google.appengine.ext.webapp import RequestHandler

from .gae_bingo import bingo

class Redirect(RequestHandler):
    def get(self):
        """ Score conversions and redirect as specified by url params

        Expects a "continue" url parameter for the destination,
        and cn_0, cn_1, ... , cn_i for the conversion names to score.
        """
        cont = self.request.get('continue')
        conversion_names = []

        index = 0
        while True:
            key = 'cn_%d' % index
            name = self.request.get(key)
            if name:
                conversion_names.append(name)
            else:
                break
            index = index + 1

        if len(conversion_names):
            bingo(conversion_names)

        self.redirect(cont)
