from __future__ import absolute_import

import request_handler
from api.auth.xsrf import ensure_xsrf_cookie

class SocratesHandler(request_handler.RequestHandler):
    @ensure_xsrf_cookie
    def get(self, path, video_id):
        if not path:
            return

        path_list = path.split('/')

        if not path_list:
            return

        topic_id = path_list[-1]
        from main import ViewVideo
        template_values = ViewVideo.show_video(self, video_id, topic_id)
        if not template_values:
            return

        template_values['has_socrates'] = True

        self.render_jinja2_template('socrates/viewvideo.html', template_values)
