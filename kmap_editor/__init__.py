import user_util
import request_handler


class MapLayoutEditor(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        self.render_jinja2_template('kmap_editor/kmap_editor.html', {})
