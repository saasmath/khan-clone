import shared_jinja
from badges import badges, util_badges
from notifications import UserNotifier

def login_notifications(user_data, continue_url):
    login_notifications = UserNotifier.pop_for_current_user_data()["login"]
    return login_notifications_html(login_notifications, user_data, continue_url)

def login_notifications_html(login_notifications, user_data, continue_url="/"):
    login_notification = None if len(login_notifications) == 0 else login_notifications[0]

    context = {"login_notification": login_notification, "continue": continue_url, "user_data":user_data}
    return shared_jinja.get().render_template("phantom_users/notifications.html", **context)

