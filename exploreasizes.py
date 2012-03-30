from api.auth.xsrf import ensure_xsrf_cookie
import request_handler

EXPLOREASIZES = [
    # Crypto
    'frequency-fingerprint',
    'frequency-stability'
]

class RequestHandler(request_handler.RequestHandler):
    @ensure_xsrf_cookie
    def get(self, exploreasize=None):
        if not exploreasize:
            self.render_jinja2_template('exploreasizes/index.html', {})
        elif exploreasize in EXPLOREASIZES:
            self.render_jinja2_template('exploreasizes/%s.html' % exploreasize, {})
        else:
            self.abort(404)
