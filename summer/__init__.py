import os
import simplejson as json
import datetime
import cookie_util
import math
import logging
import webbrowser
import urllib, urllib2

from request_handler import RequestHandler
from user_util import developer_only
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import mail

from models import UserData

class PaypalTransaction(db.Model):
    transaction_id = db.StringProperty()
    student_email = db.StringProperty()
    status = db.StringProperty()

class SummerStudent(db.Model):
    email = db.StringProperty()
    applier_email = db.StringProperty()
    application_year = db.StringProperty()
    application_status = db.StringProperty()

    first_name = db.StringProperty()
    last_name = db.StringProperty()
    date_of_birth = db.StringProperty()
    is_female = db.BooleanProperty()
    grade = db.StringProperty()
    school = db.StringProperty()
    school_zipcode = db.StringProperty()

    parent_email = db.StringProperty()
    parent_relation = db.StringProperty()

    first_choice = db.StringListProperty()
    second_choice = db.StringListProperty()
    third_choice = db.StringListProperty()
    no_choice = db.StringListProperty()
    session_1 = db.StringProperty()
    session_2 = db.StringProperty()
    session_3 = db.StringProperty()

    answer_why = db.TextProperty()
    answer_how = db.TextProperty()

    processing_fee = db.StringProperty()
    processing_fee_paid = db.BooleanProperty()

    extended_care = db.BooleanProperty()
    lunch = db.BooleanProperty()
    
    tuition = db.StringProperty()
    tuition_paid = db.BooleanProperty()

    scholarship_applied = db.BooleanProperty()
    scholarship_granted = db.BooleanProperty()
    scholarship_amount = db.StringProperty()

    self_applied = db.BooleanProperty()

    def to_dict(self):
        return dict([(p, unicode(getattr(self, p))) for p in self.properties()])

class ParentData(db.Model):
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    email = db.StringProperty()
    address_1 = db.StringProperty()
    address_2 = db.StringProperty()
    city = db.StringProperty()
    state = db.StringProperty()
    zipcode = db.StringProperty()
    country = db.StringProperty()
    phone = db.StringProperty()
    comments = db.TextProperty()
    students = db.ListProperty(db.Key)

    def to_dict(self):
        return dict([(p, unicode(getattr(self, p))) for p in self.properties()])

class PaypalIPN(RequestHandler):
    def post(self):
        self.get()

    def get(self):
        logging.info("Accessing %s" % self.request.path)
        txn_id = self.request.get('txn_id')

        query = PaypalTransaction.all()
        query.filter('transaction_id = ', txn_id)
        paypal_txn = query.get()

        if paypal_txn is None:
            logging.error("Transaction ID <%s> not found" % txn_id)
            return

        qs = self.request.query_string
        url = "https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_notify_validate&%s" % qs
        try:
            file = urllib2.urlopen(url)
            response = file.read()
        finally:
            if file:
                file.close()

        if response == "VERIFIED":
            output = qs.split('&')
            count = len(output) - 1
            paypal_attr = {}
            for i in range(1,count):
                nvp = output[i].split('=')
                paypal_attr[nvp[0]] = nvp[1]

            paypal_txn.status = paypal_attr['payment_status']

            query = SummerStudent.all()
            query.filter('email = ', paypal_txn.student_email)
            student = query.get()

            if student is None:
                logging.error("Student not found in DB for email <%s>" % student_email)
            else:
                student.processing_fee = paypal_attr['payment_gross']

                if paypal_txn.status == "Completed":
                    student.processing_fee_paid = True
                else:
                    student.processing_fee_paid = False

                student.put()

            paypal_txn.put()
        else:
            logging.error("Paypal did not verify the IPN response transaction id <%s>" % txn_id)

        return

class PaypalAutoReturn(RequestHandler):
    def post(self):
        self.get()

    def get(self):
        logging.info("Accessing %s" % self.request.path)
        student_email = self.request.get('student_email')
        user_email = self.request.get('user_email')
        txn_id = self.request.get('tx')
        #id_token = "d-bgpj-IRtoq2Fl2wbNQjgjAAWVhnZHlBihznOlZtNnEgcscBdujjOhfA18"
        id_token = "GpWfe9SEzMcEzlQptmLkJn0xLsxUAISHya6-0OZZWkzWayM0AWKT25DyLbG"

        query = PaypalTransaction.all()
        query.filter('transaction_id = ', txn_id)
        paypal_txn = query.get()

        if paypal_txn is not None:
            # This is weird, we shouldn't have found this transaction in the DB
            logging.error("Found a transaction ID <%s> already in DB for student <%s>" %
                           (txn_id, student_email))

        paypal_txn = PaypalTransaction()
        paypal_txn.transaction_id = txn_id
        paypal_txn.student_email = student_email
        paypal_txn.status = "Initiated"

        url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
        values = {
            "cmd" : "_notify-synch",
            "tx" : txn_id,
            "at" : id_token
        }

        try:
            data = urllib.urlencode(values)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            output = response.read().split('\n')
        except Exception, e:
            logging.error("Error getting transaction info from Paypal <%s>" % e)
        else:
            query = SummerStudent.all()
            query.filter('email = ', student_email)
            student = query.get()
            if student is None:
                logging.error("Student not found in DB for email <%s>" % student_email)
            else:
                count = len(output) - 1
                paypal_attr = {}
                if output[0] == "SUCCESS":
                    for i in range(1,count):
                        nvp = output[i].split('=')
                        paypal_attr[nvp[0]] = nvp[1]

                    paypal_txn.status = paypal_attr['payment_status']
                    student.processing_fee = paypal_attr['payment_gross']

                    if paypal_txn.status == "Completed":
                        student.processing_fee_paid = True
                    else:
                        student.processing_fee_paid = False
                else:
                    logging.error("Transaction %s for %s didn't succeed" % (txn_id, student_email))
                    student.processing_fee_paid = False

                student.put()

        paypal_txn.put()

        self.redirect("/summer/application-status")

class GetStudent(RequestHandler):
    def get(self):
        student_email = self.request.get('student_email')
        logging.info("Accessing %s; student %s" % (self.request.path, student_email))
        query = SummerStudent.all()
        query.filter('email = ', student_email)
        student = query.get()
        if student is None:
            output_str = json.dumps(student)
        else:
            output_str = json.dumps(student.to_dict())

        self.response.set_status(200)
        callback = self.request.get('callback')
        if callback:
            self.response.out.write("%s(%s)" % (callback, output_str))
        else:
            self.response.out.write(output_str)

        return

class Process(RequestHandler):
    def authenticated_response(self):
        user_data = UserData.current()
        user_email = user_data.user_email

        template_values = {
                "authenticated" : True,
                "user_email" : user_email,
        }

        return template_values

    @developer_only
    def get(self):
        template_values = {}
        user_data = UserData.current()

        if user_data is not None:
	    template_values = self.authenticated_response()

	else:
            template_values = {
	        "authenticated" : False,
	    }

        self.add_global_template_values(template_values)
        self.render_jinja2_template('summer/summer_process.html', template_values)


class Status(RequestHandler):
    def authenticated_response(self):
        user_data = UserData.current()
        user_email = user_data.user_email

        query = SummerStudent.all()
        query.filter('email = ', user_email)
        student = query.get()

        students = []
        is_parent = False

        if student is None:
            query = ParentData.all()
            query.filter('email = ', user_email)
            parent = query.get()
            if parent is None:
                return

            is_parent = True
            for student_key in parent.students:
                students.append(SummerStudent.get(student_key))

        else:
            students.append(student)

        template_values = {
            "authenticated" : True,
            "is_parent" : is_parent,
            "students" : students,
            "user_email" : user_email,
        }

        return template_values

    def get(self):
        template_values = {}
        user_data = UserData.current()

        if user_data is not None:
	    template_values = self.authenticated_response()
            if template_values is None:
                self.redirect("/summer/application")
                return

	else:
            template_values = {
	        "authenticated" : False,
	    }

        self.add_global_template_values(template_values)
        self.render_jinja2_template('summer/summer_status.html', template_values)

class Application(RequestHandler):
    def authenticated_response(self):
        user_data = UserData.current()
	user_email = user_data.user_email

        students = []
        is_parent = False
        query = SummerStudent.all()
        query.filter('email = ', user_email)
        student = query.get()

        if student is not None:
            students.append(student)
        else:
            query = ParentData.all()
            query.filter('email = ', user_email)
            parent = query.get()
            if parent is not None:
                is_parent = True
                for student_key in parent.students:
                    students.append(SummerStudent.get(student_key))

        if len(students) > 0:
            applied = True
            student_email = self.request.get('student_email')
            query = SummerStudent.all()
            query.filter('email = ', student_email)
            student = query.get()
            if student is None:
                logging.error("Student <%s> not expected to be NULL in datastore, but it is" % student_email)
                student = students[0]

            query = ParentData.all()
            query.filter('email = ', student.parent_email)
            parent = query.get()
            assert(parent != None)

            student_js = json.dumps(student.to_dict())
            parent_js = json.dumps(parent.to_dict())
        else:
            applied = False
            student = None
            parent = None
            student_js = json.dumps(student)
            parent_js = json.dumps(parent)

	template_values = {
	    "authenticated" : True,
	    "applied" : applied,
            "is_parent" : is_parent,
            "is_parent_js" : json.dumps(is_parent),
            "students" : students,
            "student" : student,
            "student_js" : student_js,
            "parent" : parent,
            "parent_js" : parent_js,
            "user_email_js" : json.dumps(user_email),
            "user_email" : user_email,
        }

	return template_values

    def post(self):
        self.get()

    def get(self):
	template_values = {}
        user_data = UserData.current()

        if user_data is not None:
            user_email = user_data.user_email
            application_filled = self.request.get('application_filled')
            make_payment = self.request.get('make_payment')

            if make_payment:
                student_email = self.request.get('student_email')
                is_parent_str = self.request.get('is_parent')

                query = SummerStudent.all()
                query.filter('email = ', student_email)
                student = query.get()

                if student is None:
                    output_str = 'Please <a href="/summer/application">apply</a> first' % student_email
                    self.response.out.write(output_str)
                    return

                if student.processing_fee_paid:
                    self.redirect("/summer/application-status")
                    return

                query = ParentData.all()
                query.filter('email = ', student.parent_email)
                parent = query.get()

                if parent is None:
                    logging.error("Unexpected NULL parent for student <%s> with parent <%s>" %
                                   (student_email, student.parent_email))

                if is_parent_str == "True":
                    is_parent = True
                else:
                    is_parent = False

                payee_phone_a = ""
                payee_phone_b = ""
                payee_phone_c = ""
                phone_parts = parent.phone.split("-")
                if phone_parts is not None:
                    payee_phone_a = phone_parts[0]
                    payee_phone_b = phone_parts[1]
                    payee_phone_c = phone_parts[2]

                template_values = {
                    "authenticated" : True,
                    "make_payment" : True,
                    "is_parent" : is_parent,
                    "is_parent_js" : json.dumps(is_parent),
                    "student" : student,
                    "student_js" : json.dumps(student.to_dict()),
                    "payee" : parent,
                    "payee_phone_a" : payee_phone_a,
                    "payee_phone_b" : payee_phone_b,
                    "payee_phone_c" : payee_phone_c,
                    "user_email" : user_email,
                }

            elif not application_filled:
	        template_values = self.authenticated_response()

            else:
                first_name = self.request.get('first_name')
                student_email = self.request.get('student_email')

                query = SummerStudent.all()
                query.filter('email = ', student_email)
                student = query.get()
                if student is None:
                    student = SummerStudent()
                    student.email = student_email
                    student.applier_email = user_email

                student.first_name = first_name
                student.last_name = self.request.get('last_name')

                student.date_of_birth = self.request.get('date_of_birth')

                if self.request.get('gender') == "Female":
                    student.is_female = True
                else:
                    student.is_female = False

                student.grade = self.request.get('grade')
                student.school = self.request.get('school')
                student.school_zipcode = self.request.get('school_zip')

                student.session_1 = self.request.get('session_1')
                student.session_2 = self.request.get('session_2')
                student.session_3 = self.request.get('session_3')

                session_choices = { "0":[], "1":[], "2":[], "3":[] }
                session_choices[student.session_1].append("Session 1")
                session_choices[student.session_2].append("Session 2")
                session_choices[student.session_3].append("Session 3")

                student.no_choice = session_choices["0"]
                student.first_choice = session_choices["1"]
                student.second_choice = session_choices["2"]
                student.third_choice = session_choices["3"]

                student.answer_why = self.request.get('answer_why')
                student.answer_how = self.request.get('answer_how')

                student.processing_fee = self.request.get('fee')
                student.processing_fee_paid = False

                student.tuition = 'TBD'
                student.tuition_paid = False

                student.application_year = '2012'
                student.application_status = 'Processing'

                if user_email == student_email:
                    is_parent = False
                    student.self_applied = True
                else:
                    is_parent = True
                    student.self_applied = False

                student.parent_relation = self.request.get('relation')
                student.parent_email = self.request.get('parent_email')

                student.put()

                query = ParentData.all()
                query.filter('email = ', student.parent_email)
                parent = query.get()
                if parent is None:
                    parent = ParentData()
                    parent.email = student.parent_email

                parent.first_name = self.request.get('parent_first_name')
                parent.last_name = self.request.get('parent_last_name')
                parent.address_1 = self.request.get('parent_address_1')
                parent.address_2 = self.request.get('parent_address_2')
                parent.city = self.request.get('parent_city')
                parent.state = self.request.get('parent_state')
                parent.zipcode = self.request.get('parent_zip')
                parent.country = self.request.get('parent_country')
                parent.phone = self.request.get('parent_phone')
                parent.comments = self.request.get('parent_comments')

                if student.key() not in parent.students:
                    parent.students.append(student.key())

                parent.put()

                payee_phone_a = ""
                payee_phone_b = ""
                payee_phone_c = ""
                phone_parts = parent.phone.split("-")
                if phone_parts is not None:
                    payee_phone_a = phone_parts[0]
                    payee_phone_b = phone_parts[1]
                    payee_phone_c = phone_parts[2]

                template_values = {
                    "authenticated" : True,
                    "make_payment" : True,
                    "is_parent" : is_parent,
                    "is_parent_js" : json.dumps(is_parent),
                    "student" : student,
                    "student_js" : json.dumps(student.to_dict()),
                    "parent" : parent,
                    "parent_js" : json.dumps(parent.to_dict()),
                    "payee" : parent,
                    "payee_phone_a" : payee_phone_a,
                    "payee_phone_b" : payee_phone_b,
                    "payee_phone_c" : payee_phone_c,
                    "user_email" : user_email,
                }

	else:
            template_values = {
                "authenticated" : False,
	        "applied" : False
	    }

        self.add_global_template_values(template_values)
        self.render_jinja2_template('summer/summer.html', template_values)
