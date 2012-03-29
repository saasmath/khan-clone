from api.auth.xsrf import ensure_xsrf_cookie
import request_handler

class RequestHandler(request_handler.RequestHandler):
    @ensure_xsrf_cookie
    def get(self, exploreasize=None):
        if not exploreasize:
            self.render_jinja2_template('labs/crypto/index.html', {})
        elif exploreasize == 'frequency-fingerprint':
            self.render_jinja2_template('labs/crypto/frequency-fingerprint.html', {})
        elif exploreasize == 'frequency-stability':
            self.render_jinja2_template('labs/crypto/frequency-stability.html', {})
        else:
            self.abort(404)
