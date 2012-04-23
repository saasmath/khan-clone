import datetime
import urllib

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import promo_record_model
import setting_model
import user_models
from profiles import templatetags
import request_handler
import user_util
import util
import exercise_models
import consts
from api.auth.xsrf import ensure_xsrf_cookie
from phantom_users.phantom_util import disallow_phantoms
from user_models import StudentList, UserData
from coach_resources.coach_request_model import CoachRequest
from avatars import util_avatars
from badges import util_badges

def get_last_student_list(request_handler, student_lists, use_cookie=True):
    student_lists = student_lists.fetch(100)

    # default_list is the default list for this user
    if student_lists:
        default_list = str(student_lists[0].key())
    else:
        default_list = 'allstudents'

    # desired list is the list the user asked for (via cookie or querystring)
    desired_list = None

    if use_cookie:
        cookie_val = request_handler.get_cookie_value('studentlist_id')
        desired_list = cookie_val or desired_list

    # override cookie with explicitly set querystring
    desired_list = request_handler.request_string('list_id', desired_list)

    # now validate desired_list exists
    current_list = None
    list_id = 'allstudents'
    if desired_list != 'allstudents':
        for s in student_lists:
            if str(s.key()) == desired_list:
                current_list = s
                list_id = desired_list
                break

        if current_list is None:
            list_id = default_list

    if use_cookie:
        request_handler.set_cookie('studentlist_id', list_id, max_age=2629743)

    return list_id, current_list

def get_student(coach, request_handler):
    student = request_handler.request_student_user_data(legacy=True)
    if student is None:
        raise Exception("No student found with email='%s'."
            % request_handler.request_student_email_legacy())
    if not student.is_coached_by(coach):
        raise Exception("Not your student!")
    return student

def get_student_list(coach, list_key):
    student_list = StudentList.get(list_key)
    if student_list is None:
        raise Exception("No list found with list_key='%s'." % list_key)
    if coach.key() not in student_list.coaches:
        raise Exception("Not your list!")
    return student_list

# Return a list of students, either from the list or from the user data,
# dependent on the contents of a querystring parameter.
def get_students_data(user_data, list_key=None):
    student_list = None
    if list_key and list_key != 'allstudents':
        student_list = get_student_list(user_data, list_key)

    if student_list:
        return student_list.get_students_data()
    else:
        return user_data.get_students_data()

def get_coach_student_and_student_list(request_handler):
    coach = UserData.current()
    student_list = get_student_list(coach,
        request_handler.request_string("list_id"))
    student = get_student(coach, request_handler)
    return (coach, student, student_list)

class ViewClassProfile(request_handler.RequestHandler):
    @user_util.login_required_and(phantom_user_allowed=False,
                                  child_user_allowed=False,
                                  demo_user_allowed=True)
    def get(self):
        show_coach_resources = self.request_bool('show_coach_resources', default=True)
        coach = UserData.current()

        user_override = self.request_user_data("coach_email")
        if user_override and user_override.are_students_visible_to(coach):
            # Only allow looking at a student list other than your own
            # if you are a dev, admin, or coworker.
            coach = user_override

        student_lists = StudentList.get_for_coach(coach.key())

        student_lists_list = [{
            'key': 'allstudents',
            'name': 'All students',
        }];
        for student_list in student_lists:
            student_lists_list.append({
                'key': str(student_list.key()),
                'name': student_list.name,
            })

        list_id, _ = get_last_student_list(self, student_lists, coach==UserData.current())
        current_list = None
        for student_list in student_lists_list:
            if student_list['key'] == list_id:
                current_list = student_list

        selected_graph_type = self.request_string("selected_graph_type") or ClassProgressReportGraph.GRAPH_TYPE
        if selected_graph_type == 'progressreport' or selected_graph_type == 'goals': # TomY This is temporary until all the graphs are API calls
            initial_graph_url = "/api/v1/user/students/%s?coach_email=%s&%s" % (selected_graph_type, urllib.quote(coach.email), urllib.unquote(self.request_string("graph_query_params", default="")))
        else:
            initial_graph_url = "/profile/graph/%s?coach_email=%s&%s" % (selected_graph_type, urllib.quote(coach.email), urllib.unquote(self.request_string("graph_query_params", default="")))
        initial_graph_url += 'list_id=%s' % list_id

        template_values = {
                'user_data_coach': coach,
                'coach_email': coach.email,
                'list_id': list_id,
                'student_list': current_list,
                'student_lists': student_lists_list,
                'student_lists_json': json.dumps(student_lists_list),
                'coach_nickname': coach.nickname,
                'selected_graph_type': selected_graph_type,
                'initial_graph_url': initial_graph_url,
                'exercises': exercise_models.Exercise.get_all_use_cache(),
                'is_profile_empty': not coach.has_students(),
                'selected_nav_link': 'coach',
                "view": self.request_string("view", default=""),
                'stats_charts_class': 'coach-view',
                }
        self.render_jinja2_template('viewclassprofile.html', template_values)

class ViewProfile(request_handler.RequestHandler):
    # TODO(sundar) - add login_required_special(demo_allowed = True)
    # However, here only the profile of the students of the demo account are allowed
    @user_util.open_access
    @ensure_xsrf_cookie
    def get(self, email_or_username=None, subpath=None):

        """Render a student profile.

        Keyword arguments:
        email_or_username -- matches the first grouping in /profile/(.+?)/(.*)
        subpath -- matches the second grouping, and is ignored server-side,
        but is used to route client-side

        """
        current_user_data = UserData.current() or UserData.pre_phantom()

        if current_user_data.is_pre_phantom and email_or_username is None:
            # Pre-phantom users don't have any profiles - just redirect them
            # to the homepage if they try to view their own.
            self.redirect(util.create_login_url(self.request.uri))
            return

        if not email_or_username:
            user_data = current_user_data
        elif email_or_username == 'nouser' and current_user_data.is_phantom:
            user_data = current_user_data
        else:
            user_data = UserData.get_from_url_segment(email_or_username)
            if (user_models.UniqueUsername.is_valid_username(email_or_username)
                    and user_data
                    and user_data.username
                    and user_data.username != email_or_username):
                # The path segment is a username and resolved to the user,
                # but is not actually their canonical name. Redirect to the
                # canonical version.
                if subpath:
                    self.redirect("/profile/%s/%s" % (user_data.username,
                                                      subpath))
                else:
                    self.redirect("/profile/%s" % user_data.username)
                return


        profile = UserProfile.from_user(user_data, current_user_data)

        if profile is None:
            self.render_jinja2_template('noprofile.html', {})
            return

        is_self = user_data.user_id == current_user_data.user_id
        show_intro = False

        if is_self:
            promo_record = promo_record_model.PromoRecord.get_for_values(
                    "New Profile Promo", user_data.user_id)

            if promo_record is None:
                # The user has never seen the new profile page! Show a tour.
                if subpath:
                    # But if they're not on the root profile page, force them.
                    self.redirect("/profile")
                    return

                show_intro = True
                promo_record_model.PromoRecord.record_promo("New Profile Promo",
                                                user_data.user_id,
                                                skip_check=True)

        has_full_access = is_self or user_data.is_visible_to(current_user_data)
        tz_offset = self.request_int("tz_offset", default=0)

        template_values = {
            'show_intro': show_intro,
            'profile': profile,
            'tz_offset': tz_offset,
            'count_videos': setting_model.Setting.count_videos(),
            'count_exercises': exercise_models.Exercise.get_count(),
            'user_data_student': user_data if has_full_access else None,
            'profile_root': user_data.profile_root,
            "view": self.request_string("view", default=""),
        }
        self.render_jinja2_template('viewprofile.html', template_values)


class UserProfile(object):
    """ Profile information about a user.

    This is a transient object and derived from the information in UserData,
    and formatted/tailored for use as an object about a user's public profile.
    """

    def __init__(self):
        self.username = None
        self.profile_root = "/profile"
        self.email = ""
        self.is_phantom = True
        
        # Indicates whether or not the profile has been marked public. Not
        # necessarily indicative of what fields are currently filled in this
        # current instance, as different projections may differ on actor
        # privileges
        self.is_public = False

        # Whether or not the app is able to collect data about the user.
        # Note users under 13 without parental consent cannot give private data.
        self.is_data_collectible = False
        
        self.is_coaching_logged_in_user = False
        self.is_requesting_to_coach_logged_in_user = False

        self.nickname = ""
        self.date_joined = ""
        self.points = 0
        self.count_videos_completed = 0
        self.count_exercises_proficient = 0
        self.public_badges = []

        default_avatar = util_avatars.avatar_for_name()
        self.avatar_name = default_avatar.name
        self.avatar_src = default_avatar.image_src

    @staticmethod
    def from_user(user, actor):
        """ Retrieve profile information about a user for the specified actor.

        This will do the appropriate ACL checks and return the greatest amount
        of profile data that the actor has access to, or None if no access
        is allowed.

        user - user_models.UserData object to retrieve information from
        actor - user_models.UserData object corresponding to who is requesting
                the data
        """
        
        if user is None:
            return None

        is_self = user.user_id == actor.user_id
        user_is_visible_to_actor = user.is_visible_to(actor)
        actor_is_visible_to_user = actor.is_visible_to(user)

        if is_self or user_is_visible_to_actor:
            # Full data about the user
            return UserProfile._from_user_internal(
                    user,
                    full_projection=True,
                    is_coaching_logged_in_user=actor_is_visible_to_user,
                    is_self=is_self)
        elif user.has_public_profile():
            # Return only public data
            return UserProfile._from_user_internal(
                    user,
                    full_projection=False,
                    is_coaching_logged_in_user=actor_is_visible_to_user)
        else:
            return None

    @staticmethod
    def _from_user_internal(user,
                            full_projection=False,
                            is_coaching_logged_in_user=False,
                            is_self=False):

        profile = UserProfile()

        profile.username = user.username
        profile.nickname = user.nickname
        profile.date_joined = user.joined
        avatar = util_avatars.avatar_for_name(user.avatar_name)
        profile.avatar_name = avatar.name
        profile.avatar_src = avatar.image_src
        profile.public_badges = util_badges.get_public_user_badges(user)
        profile.points = user.points
        profile.count_videos_completed = user.get_videos_completed()
        profile.count_exercises_proficient = len(user.all_proficient_exercises)

        profile.is_self = is_self
        profile.is_coaching_logged_in_user = is_coaching_logged_in_user
        profile.is_phantom = user.is_phantom

        profile.is_public = user.has_public_profile()

        if profile.is_public or full_projection:
            profile.profile_root = user.profile_root

        if full_projection:
            profile.email = user.email
            profile.is_data_collectible = (not user.is_child_account() and
                                           not user.is_maybe_edu_account())

        return profile

    @staticmethod
    def get_coach_and_requester_profiles_for_student(student_user_data):
        coach_profiles = []

        for coach_user_data in student_user_data.get_coaches_data():
            profile = UserProfile._from_coach(coach_user_data, student_user_data)
            coach_profiles.append(profile)

        requests = CoachRequest.get_for_student(student_user_data)
        for request in requests:
            coach_user_data = request.coach_requesting_data
            profile = UserProfile._from_coach(coach_user_data, student_user_data)
            coach_profiles.append(profile)

        return coach_profiles

    @staticmethod
    def _from_coach(coach, actor):
        """ Retrieve profile information about a coach for the specified actor.

        At minimum, this will return a UserProfile with the following data:
        -- email
        -- is_coaching_logged_in_user
        -- is_requesting_to_coach_logged_in_user
        
        If the coach has a public profile or if she is coached by the actor,
        more information will be retrieved as allowed.
        
        coach - user_models.UserData object to retrieve information from
        actor - user_models.UserData object corresponding to who is requesting
                the data

        TODO(marcia): Move away from using email to manage coaches, since
        this breaks our notions of public/private profiles.
        
        """

        profile = UserProfile.from_user(coach, actor) or UserProfile()

        profile.email = coach.email

        is_coach = actor.is_coached_by(coach)
        profile.is_coaching_logged_in_user = is_coach
        profile.is_requesting_to_coach_logged_in_user = not is_coach

        return profile

class ProfileGraph(request_handler.RequestHandler):

    @user_util.open_access    # TODO(csilvers): is this right? -- ask marcia
    def get(self):
        html = ""
        json_update = ""

        user_data_target = self.get_profile_target_user_data()
        if user_data_target:
            if self.redirect_if_not_ajax(user_data_target):
                return

            if self.request_bool("update", default=False):
                json_update = self.json_update(user_data_target)
            else:
                html_and_context = self.graph_html_and_context(user_data_target)

                if html_and_context["context"].has_key("is_graph_empty") and html_and_context["context"]["is_graph_empty"]:
                    # This graph is empty of activity. If it's a date-restricted graph, see if bumping out the time restrictions can help.
                    if self.redirect_for_more_data():
                        return

                html = html_and_context["html"]

        if len(json_update) > 0:
            self.response.out.write(json_update)
        else:
            self.response.out.write(html)

    def get_profile_target_user_data(self):
        email = self.request_student_email_legacy()
        # TODO: ACL
        return UserData.get_possibly_current_user(email)

    def redirect_if_not_ajax(self, student):
        if not self.is_ajax_request():
            # If it's not an ajax request, redirect to the appropriate /profile URL
            self.redirect("/profile?selected_graph_type=%s&student_email=%s&graph_query_params=%s" %
                    (self.GRAPH_TYPE, urllib.quote(student.email), urllib.quote(urllib.quote(self.request.query_string))))
            return True
        return False

    def redirect_for_more_data(self):
        return False

    def json_update(self, user_data):
        return ""

class ClassProfileGraph(ProfileGraph):
    def get_profile_target_user_data(self):
        coach = UserData.current()

        if coach:
            user_override = self.request_user_data("coach_email")
            if user_override and user_override.are_students_visible_to(coach):
                # Only allow looking at a student list other than your own
                # if you are a dev, admin, or coworker.
                coach = user_override

        return coach

    def redirect_if_not_ajax(self, coach):
        if not self.is_ajax_request():
            # If it's not an ajax request, redirect to the appropriate /profile URL
            self.redirect("/class_profile?selected_graph_type=%s&coach_email=%s&graph_query_params=%s" %
                    (self.GRAPH_TYPE, urllib.quote(coach.email), urllib.quote(urllib.quote(self.request.query_string))))
            return True
        return False

    def get_student_list(self, coach):
        student_lists = StudentList.get_for_coach(coach.key())
        _, actual_list = get_last_student_list(self, student_lists, coach.key()==UserData.current().key())
        return actual_list

class ProfileDateToolsGraph(ProfileGraph):

    DATE_FORMAT = "%Y-%m-%d"

    @staticmethod
    def inclusive_start_date(dt):
        return datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0) # Inclusive of start date

    @staticmethod
    def inclusive_end_date(dt):
        return datetime.datetime(dt.year, dt.month, dt.day, 23, 59, 59) # Inclusive of end date

    def request_date_ctz(self, key):
        # Always work w/ client timezone dates on the client and UTC dates on the server
        dt = self.request_date(key, self.DATE_FORMAT, default=datetime.datetime.min)
        if dt == datetime.datetime.min:
            s_dt = self.request_string(key, default="")
            if s_dt == "today":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()))
            elif s_dt == "yesterday":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()) - datetime.timedelta(days=1))
            elif s_dt == "lastweek":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()) - datetime.timedelta(days=6))
            elif s_dt == "lastmonth":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()) - datetime.timedelta(days=29))
        return dt

    def tz_offset(self):
        return self.request_int("tz_offset", default=0)

    def ctz_to_utc(self, dt_ctz):
        return dt_ctz - datetime.timedelta(minutes=self.tz_offset())

    def utc_to_ctz(self, dt_utc):
        return dt_utc + datetime.timedelta(minutes=self.tz_offset())

class ClassProfileDateGraph(ClassProfileGraph, ProfileDateToolsGraph):

    DATE_FORMAT = "%m/%d/%Y"

    def get_date(self):
        dt_ctz = self.request_date_ctz("dt")

        if dt_ctz == datetime.datetime.min:
            # If no date, assume looking at today
            dt_ctz = self.utc_to_ctz(datetime.datetime.now())

        return self.ctz_to_utc(self.inclusive_start_date(dt_ctz))

class ProfileDateRangeGraph(ProfileDateToolsGraph):

    def get_start_date(self):
        dt_ctz = self.request_date_ctz("dt_start")

        if dt_ctz == datetime.datetime.min:
            # If no start date, assume looking at last 7 days
            dt_ctz = self.utc_to_ctz(datetime.datetime.now() - datetime.timedelta(days=6))

        return self.ctz_to_utc(self.inclusive_start_date(dt_ctz))

    def get_end_date(self):
        dt_ctz = self.request_date_ctz("dt_end")
        dt_start_ctz_test = self.request_date_ctz("dt_start")
        dt_start_ctz = self.utc_to_ctz(self.get_start_date())

        if (dt_ctz == datetime.datetime.min and dt_start_ctz_test == datetime.datetime.min):
            # If no end date or start date specified, assume looking at 7 days after start date
            dt_ctz = dt_start_ctz + datetime.timedelta(days=6)
        elif dt_ctz == datetime.datetime.min:
            # If start date specified but no end date, assume one day
            dt_ctz = dt_start_ctz

        if (dt_ctz - dt_start_ctz).days > consts.MAX_GRAPH_DAY_RANGE or dt_start_ctz > dt_ctz:
            # Maximum range of 30 days for now
            dt_ctz = dt_start_ctz + datetime.timedelta(days=consts.MAX_GRAPH_DAY_RANGE)

        return self.ctz_to_utc(self.inclusive_end_date(dt_ctz))

    def redirect_for_more_data(self):
        dt_start_ctz_test = self.request_date_ctz("dt_start")
        dt_end_ctz_test = self.request_date_ctz("dt_end")

        # If no dates were specified and activity was empty, try max day range instead of default 7.
        if dt_start_ctz_test == datetime.datetime.min and dt_end_ctz_test == datetime.datetime.min:
            self.redirect(self.request_url_with_additional_query_params("dt_start=lastmonth&dt_end=today&is_ajax_override=1"))
            return True

        return False

# TODO(sundar) - add login_required_special(demo_allowed = True)
# However, here only the profile of the students of the demo account are allowed
class ActivityGraph(ProfileDateRangeGraph):
    GRAPH_TYPE = "activity"
    def graph_html_and_context(self, student):
        return templatetags.profile_activity_graph(student, self.get_start_date(), self.get_end_date(), self.tz_offset())

# TODO(sundar) - add login_required_special(demo_allowed = True)
# However, here only the profile of the students of the demo account are allowed
class FocusGraph(ProfileDateRangeGraph):
    GRAPH_TYPE = "focus"
    def graph_html_and_context(self, student):
        return templatetags.profile_focus_graph(student, self.get_start_date(), self.get_end_date())

# TODO(sundar) - add login_required_special(demo_allowed = True)
# However, here only the profile of the students of the demo account are allowed
class ExercisesOverTimeGraph(ProfileGraph):
    GRAPH_TYPE = "exercisesovertime"
    def graph_html_and_context(self, student):
        return templatetags.profile_exercises_over_time_graph(student)

# TODO(sundar) - add login_required_special(demo_allowed = True)
# However, here only the profile of the students of the demo account are allowed
class ExerciseProblemsGraph(ProfileGraph):
    GRAPH_TYPE = "exerciseproblems"
    def graph_html_and_context(self, student):
        return templatetags.profile_exercise_problems_graph(student, self.request_string("exercise_name"))

# TODO(sundar) - add login_required_special(demo_allowed = True)
class ClassExercisesOverTimeGraph(ClassProfileGraph):
    GRAPH_TYPE = "classexercisesovertime"
    def graph_html_and_context(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_exercises_over_time_graph(coach, student_list)

# TODO(sundar) - add login_required_special(demo_allowed = True)
class ClassProgressReportGraph(ClassProfileGraph):
    GRAPH_TYPE = "progressreport"

# TODO(sundar) - add login_required_special(demo_allowed = True)
class ClassTimeGraph(ClassProfileDateGraph):
    GRAPH_TYPE = "classtime"
    def graph_html_and_context(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_time_graph(coach, self.get_date(), self.tz_offset(), student_list)

# TODO(sundar) - add login_required_special(demo_allowed = True)
class ClassEnergyPointsPerMinuteGraph(ClassProfileGraph):
    GRAPH_TYPE = "classenergypointsperminute"
    def graph_html_and_context(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_energy_points_per_minute_graph(coach, student_list)

    def json_update(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_energy_points_per_minute_update(coach, student_list)
