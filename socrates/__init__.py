from __future__ import absolute_import

import request_handler
from api.auth.xsrf import ensure_xsrf_cookie

class SocratesHandler(request_handler.RequestHandler):
    @ensure_xsrf_cookie
    def get(self, readable_id=""):
        import main
        template_values = main.ViewVideo.get_template_data(self, readable_id,
            redirect_allowed=False)
        template_values['has_socrates'] = True
        self.render_jinja2_template('socrates/viewvideo.html', template_values)
