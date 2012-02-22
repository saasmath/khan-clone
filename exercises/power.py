import request_handler
from api.auth.xsrf import ensure_xsrf_cookie

class ViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, exid):
        self.render_jinja2_template("exercises/power_template.html", {})
