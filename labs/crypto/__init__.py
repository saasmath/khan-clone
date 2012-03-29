from api.auth.xsrf import ensure_xsrf_cookie
import request_handler

class RequestHandler(request_handler.RequestHandler):
    @ensure_xsrf_cookie
    def get(self):
        self.render_jinja2_template('labs/crypto/index.html', {})
