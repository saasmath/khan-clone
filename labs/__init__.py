import request_handler
import user_util
from api.auth.xsrf import ensure_xsrf_cookie


class LabsRequestHandler(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('labs/labs.html', {})


class LabsCSRequestHandler(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('canvas-editor/cs.html', {})


class LabsCSEditorRequestHandler(request_handler.RequestHandler):

    @user_util.developer_only
    @ensure_xsrf_cookie
    def get(self):
        self.render_jinja2_template('canvas-editor/editor.html', {})


class LabsCSExerciseRequestHandler(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    @user_util.open_access
    def get(self):
        self.render_jinja2_template('canvas-editor/exercise.html', {})


class LabsCSRecordRequestHandler(request_handler.RequestHandler):

    @user_util.developer_only
    @ensure_xsrf_cookie
    def get(self):
        self.render_jinja2_template('canvas-editor/record.html', {})
