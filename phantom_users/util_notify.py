from exercises import exercise_models
from notifications import UserNotifier
import request_handler
import user_util


def welcome(user_data):
    if user_data == None:
        return False
    UserNotifier.push_login_for_user_data(user_data, "Welcome to Khan Academy! To get the best experience you should [login]")


def update(user_data, user_exercise, threshold=False, isProf=False, gotBadge=False):
    if user_data == None:
        return False

    if not user_data.is_phantom:
        return False

    numquest = None

    if user_exercise != None:
        numquest = user_exercise.total_done
        prof = str(exercise_models.Exercise.to_display_name(user_exercise.exercise))

    numbadge = user_data.badges
    numpoint = user_data.points

    # First question
    if (numquest == 1):
        UserNotifier.push_login_for_user_data(user_data, "You&rsquo;ve answered your first question! You should [login]")
    # Every 10 questions, more than 20 every 5
    if (numquest != None and numquest % 10 == 0) or \
       (numquest != None and numquest > 20 and numquest % 5 == 0):
        UserNotifier.push_login_for_user_data(user_data, "You&rsquo;ve answered %d questions! You should [login]" % numquest)
    #Proficiency
    if isProf:
        UserNotifier.push_login_for_user_data(user_data, "You&rsquo;re proficient in %s. You should [login]" % prof)
    #First Badge
    if numbadge != None and len(numbadge) == 1 and gotBadge:
        achievements_url = "%s/achievements" % user_data.profile_root
        UserNotifier.push_login_for_user_data(
                user_data,
                "Congrats on your first <a href='%s'>badge</a>! You should [login]" %
                        achievements_url)
    #Every badge after
    if numbadge != None and len(numbadge) > 1 and gotBadge:
        UserNotifier.push_login_for_user_data(user_data, "You&rsquo;ve earned <a href='/profile'>%d badges</a> so far. You should [login]" % len(numbadge))
    #Every 2.5k points
    if numpoint != None and threshold:
        numpoint = 2500 * (numpoint / 2500) + 2500
        UserNotifier.push_login_for_user_data(user_data, "You&rsquo;ve earned over <a href='/profile'>%d points</a>! You should [login]" % numpoint)


#Toggle Notify allows the user to close the notification bar (by deleting the memcache) until a new notification occurs.
class ToggleNotify(request_handler.RequestHandler):
    @user_util.open_access
    def post(self):
        UserNotifier.clear_login()
