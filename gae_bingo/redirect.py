from google.appengine.ext.webapp import RequestHandler

from .gae_bingo import bingo

class Redirect(RequestHandler):
    def get(self):
        """ Score conversions and redirect as specified by url params

        Expects a 'continue' url parameter for the destination,
        and a 'conversion_name' url parameter for each conversion to score.
        """
        cont = self.request.get('continue', default_value='/')
        conversion_names = self.request.get_all('conversion_name')

        if len(conversion_names):
            bingo(conversion_names)

        self.redirect(cont)
