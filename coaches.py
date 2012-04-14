# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from app import App
import app
import custom_exceptions
import facebook_util
import util
import user_util
import request_handler

from user_models import UserData, StudentList
from coach_resources.coach_request_model import CoachRequest
from badges import util_badges

from profiles.util_profile import ExercisesOverTimeGraph, ExerciseProblemsGraph
from profiles.util_profile import ClassProgressReportGraph, ClassEnergyPointsPerMinuteGraph, ClassTimeGraph

from phantom_users.phantom_util import disallow_phantoms
import profiles.util_profile as util_profile
from api.auth.xsrf import ensure_xsrf_cookie

def update_coaches_and_requests(user_data, coaches_json):
    """ Update the user's coaches and requests.
    
    Expects a list of jsonified UserProfiles, where an
    isCoachingLoggedInUser value of True indicates a coach relationship,
    and a value of False indicates a pending request.
    
    Any extant coach or request relationships not represented in
    coaches_json will be deleted.
    """
    requester_emails = update_coaches(user_data, coaches_json)
    update_requests(user_data, requester_emails)
    return util_profile.UserProfile.get_coach_and_requester_profiles_for_student(user_data)

def update_coaches(user_data, coaches_json):
    """ Add as coaches those in coaches_json with isCoachingLoggedInUser
    value True, and remove any old coaches not in coaches_json.
    
    Return a list of requesters' emails.
    """
    updated_coach_key_emails = []
    current_coaches_data = user_data.get_coaches_data()
    outstanding_coaches_dict = dict([(coach.email, coach.key_email)
            for coach in current_coaches_data])
    requester_emails = []

    for coach_json in coaches_json:
        email = coach_json['email']
        is_coaching_logged_in_user = coach_json['isCoachingLoggedInUser']
        if is_coaching_logged_in_user:
            if email in outstanding_coaches_dict:
                # Email corresponds to a current coach
                updated_coach_key_emails.append(outstanding_coaches_dict[email])
                del outstanding_coaches_dict[email]
            else:
                # Look up this new coach's key_email
                coach_user_data = UserData.get_from_username_or_email(email)
                if coach_user_data is not None:
                    updated_coach_key_emails.append(coach_user_data.key_email)
                else:
                    raise custom_exceptions.InvalidEmailException()
        else:
            requester_emails.append(email)

    user_data.remove_student_lists(outstanding_coaches_dict.keys())
    user_data.coaches = updated_coach_key_emails
    user_data.put()

    return requester_emails

def update_requests(user_data, requester_emails):
    """ Remove all CoachRequests not represented by requester_emails.
    """
    current_requests = CoachRequest.get_for_student(user_data)

    for current_request in current_requests:
        coach_email = current_request.coach_requesting_data.email
        if coach_email not in requester_emails:
            current_request.delete()

class ViewCoaches(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.open_access
    def get(self):
        """ Redirect legacy /coaches to profile page's coaches tab.
        """
        user_data = UserData.current()
        if user_data:
            self.redirect(user_data.profile_root + "coaches")
        else:
            self.redirect(util.create_login_url(self.request.uri))


class ViewStudents(request_handler.RequestHandler):
    @disallow_phantoms
    @ensure_xsrf_cookie
    @user_util.open_access
    def get(self):
        user_data = UserData.current()
        if user_data:

            user_data_override = self.request_user_data("coach_email")
            if user_util.is_current_user_developer() and user_data_override:
                user_data = user_data_override

            invalid_student = self.request_bool("invalid_student", default = False)

            coach_requests = [x.student_requested_data.email for x in CoachRequest.get_for_coach(user_data) if x.student_requested_data]

            student_lists_models = StudentList.get_for_coach(user_data.key())
            student_lists_list = [];
            for student_list in student_lists_models:
                student_lists_list.append({
                    'key': str(student_list.key()),
                    'name': student_list.name,
                })
            student_lists_dict = dict((g['key'], g) for g in student_lists_list)

            students_data = user_data.get_students_data()
            students = map(lambda s: {
                'key': str(s.key()),
                'email': s.email,
                'nickname': s.nickname,
                'profile_root': s.profile_root,
                'studentLists': [l for l in [student_lists_dict.get(str(list_id)) for list_id in s.student_lists] if l],
            }, students_data)
            students.sort(key=lambda s: s['nickname'])

            template_values = {
                'students': students,
                'students_json': json.dumps(students),
                'student_lists': student_lists_list,
                'student_lists_json': json.dumps(student_lists_list),
                'invalid_student': invalid_student,
                'coach_requests': coach_requests,
                'coach_requests_json': json.dumps(coach_requests),
                'selected_nav_link': 'coach',
                'email': user_data.email,
            }
            self.render_jinja2_template('viewstudentlists.html', template_values)
        else:
            self.redirect(util.create_login_url(self.request.uri))

class RequestStudent(request_handler.RequestHandler):
    @disallow_phantoms
    @user_util.manual_access_checking
    def post(self):
        user_data = UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        user_data_student = self.request_user_data("student_email")
        if user_data_student:
            if not user_data_student.is_coached_by(user_data):
                coach_request = CoachRequest.get_or_insert_for(user_data, user_data_student)
                if coach_request:
                    if not self.is_ajax_request():
                        self.redirect("/students")
                    return

        if self.is_ajax_request():
            self.response.set_status(404)
        else:
            self.redirect("/students?invalid_student=1")

class AcceptCoach(request_handler.RequestHandler):
    @user_util.manual_access_checking
    @request_handler.RequestHandler.exceptions_to_http(400)
    @disallow_phantoms
    def get(self):
        """ Only used when a coach deletes a request in studentlists.js.
        """
        user_data = UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        accept_coach = self.request_bool("accept", default = False)
        user_data_coach = self.request_user_data("coach_email")
        user_data_student = self.request_user_data('student_email')

        if bool(user_data_coach) == bool(user_data_student):
            raise Exception('must provide coach_email xor student_email')

        if user_data_coach:
            user_data_student = user_data
        elif user_data_student:
            user_data_coach = user_data

        if user_data_coach and not user_data_student.is_coached_by(user_data_coach):
            coach_request = CoachRequest.get_for(user_data_coach, user_data_student)
            if coach_request:
                coach_request.delete()

                if user_data.key_email == user_data_student.key_email and accept_coach:
                    user_data_student.coaches.append(user_data_coach.key_email)
                    user_data_student.put()

        if not self.is_ajax_request():
            self.redirect("/coaches")

class UnregisterStudentCoach(request_handler.RequestHandler):
    @staticmethod
    def remove_student_from_coach(student, coach):
        if student.student_lists:
            actual_lists = StudentList.get(student.student_lists)
            student.student_lists = [l.key() for l in actual_lists if coach.key() not in l.coaches]

        try:
            student.coaches.remove(coach.key_email)
        except ValueError:
            pass

        try:
            student.coaches.remove(coach.key_email.lower())
        except ValueError:
            pass

        student.put()

    def do_request(self, student, coach, redirect_to):
        if not UserData.current():
            self.redirect(util.create_login_url(self.request.uri))
            return

        if student and coach:
            self.remove_student_from_coach(student, coach)

        if not self.is_ajax_request():
            self.redirect(redirect_to)

class UnregisterStudent(UnregisterStudentCoach):
    @disallow_phantoms
    @user_util.open_access
    def get(self):
        user_data = UserData.current()
        return self.do_request(
            self.request_user_data("student_email"),
            UserData.current(),
            "/students"
        )

class AddStudentToList(request_handler.RequestHandler):
    @user_util.open_access
    @request_handler.RequestHandler.exceptions_to_http(400)
    def post(self):
        user_data = UserData.current()

        coach_data, student_data, student_list = util_profile.get_coach_student_and_student_list(self)

        if student_list.key() in student_data.student_lists:
            raise Exception("Student %s is already in list %s" % (student_data.key(), student_list.key()))

        student_data.student_lists.append(student_list.key())
        student_data.put()

class RemoveStudentFromList(request_handler.RequestHandler):
    @user_util.open_access
    @request_handler.RequestHandler.exceptions_to_http(400)
    def post(self):
        user_data = UserData.current()

        coach_data, student_data, student_list = util_profile.get_coach_student_and_student_list(self)

        # due to a bug, we have duplicate lists in the collection. fix this:
        student_data.student_lists = list(set(student_data.student_lists))

        student_data.student_lists.remove(student_list.key())
        student_data.put()
