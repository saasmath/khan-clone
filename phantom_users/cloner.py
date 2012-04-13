import request_handler
import user_util


class Clone(request_handler.RequestHandler):
    @user_util.open_access
    def get(self):
        title = "Please wait while we copy your data to your new account."
        message_html = ("We're in the process of copying over all of the "
                        "progress you've made. You may access your account "
                        "once the transfer is complete.")
        sub_message_html = ("This process can take a long time, thank you for "
                            "your patience.")
        cont = self.request_continue_url()
        self.render_jinja2_template('phantom_users/transfer.html', {
            'title': title,
            'message_html': message_html,
            'sub_message_html': sub_message_html,
            'dest_url': cont,
        })
