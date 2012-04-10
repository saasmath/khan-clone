"""Holds UserData, UniqueUsername, NicknameIndex, UnverifiedUser, StudentList.

UserData: database entity holding information about a single registered user
UniqueUsername: database entity of usernames that've been set on profile pages
NicknameIndex: database entity allowing search for users by their nicknames
UnverifiedUser: holds info on users in the midst of the signup process
StudentList: a list of users associated with a single coach.

A 'user' is an entity that logs into Khan Academy in some way (there
are also some 'fake' users that do not require logging in, like the
phantom user).
"""

import datetime
import logging
import os
import re
import urllib

from google.appengine.api import datastore_errors, users
from google.appengine.ext import db

import accuracy_model
from api import jsonify   # TODO(csilvers): move out of api/?
import auth.models
from auth import age_util
from counters import user_counter
from discussion import models_discussion
import badges
import facebook_util
import gae_bingo.models
import nicknames
import object_property
import phantom_users
import request_cache
import transaction_util
import util


_PRE_PHANTOM_EMAIL = "http://nouserid.khanacademy.org/pre-phantom-user-2"


# Demo user khanacademy.demo2@gmail.com is a coworker of khanacademy.demo@gmail.com
# khanacademy.demo@gmail.com is coach of a bunch of Khan staff and LASD staff, which is shared
# with users as a demo. Access to the demo is via /api/auth/token_to_session with
# oauth tokens for khanacademy.demo2@gmail.com supplied via secrets.py
_COACH_DEMO_COWORKER_EMAIL = "khanacademy.demo2@gmail.com"


class UserData(gae_bingo.models.GAEBingoIdentityModel,
               auth.models.CredentialedUser, db.Model):
    # Canonical reference to the user entity. Avoid referencing this directly
    # as the fields of this property can change; only the ID is stable and
    # user_id can be used as a unique identifier instead.
    user = db.UserProperty()

    # Deprecated - this was used to represent the current e-mail address of the
    # user but is no longer relevant. Do not use - see user_id instead.
    current_user = db.UserProperty()

    # An opaque and uniquely identifying string for a user - this is stable
    # even if the user changes her e-mail.
    user_id = db.StringProperty()

    # A uniquely identifying string for a user. This is not stable and can
    # change if a user changes her e-mail. This is not actually always an
    # e-mail; for non-Google users, this can be a
    # URI like http://facebookid.khanacademy.org/1234
    user_email = db.StringProperty()

    # A human-readable name that will be user-configurable.
    # Do not read or modify this directly! Instead, use the nickname property
    # and update_nickname method
    user_nickname = db.StringProperty(indexed=False)

    # A globally unique user-specified username,
    # which will be used in URLS like khanacademy.org/profile/<username>
    username = db.StringProperty(default="")
    
    moderator = db.BooleanProperty(default=False)
    developer = db.BooleanProperty(default=False)

    # Account creation date in UTC
    joined = db.DateTimeProperty(auto_now_add=True)
    
    # Last login date in UTC. Note that this was incorrectly set, and could
    # have stale values (though is always non-empty) for users who have never
    # logged in prior to the launch of our own password based logins(2012-04-12)
    last_login = db.DateTimeProperty(indexed=False)

    # Whether or not user has been hellbanned from community participation
    # by a moderator
    discussion_banned = db.BooleanProperty(default=False)

    # Names of exercises in which the user is *explicitly* proficient
    proficient_exercises = object_property.StringListCompatTsvProperty()

    # Names of all exercises in which the user is proficient
    all_proficient_exercises = object_property.StringListCompatTsvProperty()

    suggested_exercises = object_property.StringListCompatTsvProperty()
    badges = object_property.StringListCompatTsvProperty() # All awarded badges
    need_to_reassess = db.BooleanProperty(indexed=False)
    points = db.IntegerProperty(default=0)
    total_seconds_watched = db.IntegerProperty(default=0)

    # A list of email values corresponding to the "user" property of the coaches
    # for the user. Note: that it may not be the current, active email
    coaches = db.StringListProperty()

    coworkers = db.StringListProperty()
    student_lists = db.ListProperty(db.Key)
    map_coords = db.StringProperty(indexed=False)
    videos_completed = db.IntegerProperty(default=-1)
    last_daily_summary = db.DateTimeProperty(indexed=False)
    last_badge_review = db.DateTimeProperty(indexed=False)
    last_activity = db.DateTimeProperty(indexed=False)
    start_consecutive_activity_date = db.DateTimeProperty(indexed=False)
    count_feedback_notification = db.IntegerProperty(default= -1, indexed=False)
    question_sort_order = db.IntegerProperty(default= -1, indexed=False)
    uservideocss_version = db.IntegerProperty(default=0, indexed=False)
    has_current_goals = db.BooleanProperty(default=False, indexed=False)

    # A list of badge names that the user has chosen to display publicly
    # Note that this list is not contiguous - it may have "holes" in it
    # indicated by the reserved string "__empty__"
    public_badges = object_property.TsvProperty()

    # The name of the avatar the user has chosen. See avatar.util_avatar.py
    avatar_name = db.StringProperty(indexed=False)

    # The user's birthday was only relatively recently collected (Mar 2012)
    # so older UserData may not have this information.
    birthdate = db.DateProperty(indexed=False)
    
    # The user's gender is optional, and only collected as of Mar 2012,
    # so older UserData may not have this information.
    gender = db.StringProperty(indexed=False)

    # Whether or not the user has indicated she wishes to have a public
    # profile (and can be searched, etc)
    is_profile_public = db.BooleanProperty(default=False, indexed=False)

    _serialize_blacklist = [
            "badges", "count_feedback_notification",
            "last_daily_summary", "need_to_reassess", "videos_completed",
            "moderator", "question_sort_order",
            "last_login", "user", "current_user", "map_coords",
            "user_nickname", "user_email",
            "seconds_since_joined", "has_current_goals", "public_badges",
            "avatar_name", "username", "is_profile_public",
            "credential_version", "birthdate", "gender",
            "conversion_test_hard_exercises",
            "conversion_test_easy_exercises",
    ]

    conversion_test_hard_exercises = set(['order_of_operations', 'graphing_points',
        'probability_1', 'domain_of_a_function', 'division_4',
        'ratio_word_problems', 'writing_expressions_1', 'ordering_numbers',
        'geometry_1', 'converting_mixed_numbers_and_improper_fractions'])
    conversion_test_easy_exercises = set(['counting_1', 'significant_figures_1', 'subtraction_1'])

    @property
    def nickname(self):
        """ Gets a human-friendly display name that the user can optionally set
        themselves. Will initially default to either the Facebook name or
        part of the user's e-mail.
        """

        # Note - we make a distinction between "None", which means the user has
        # never gotten or set their nickname, and the empty string, which means
        # the user has explicitly made an empty nickname
        if self.user_nickname is not None:
            return self.user_nickname

        return nicknames.get_default_nickname_for(self)

    def update_nickname(self, nickname=None):
        """ Updates the user's nickname and relevant indices and persists
        to the datastore.
        """
        if nickname is None:
            nickname = nicknames.get_default_nickname_for(self)
        new_name = nickname or ""

        # TODO: Fix this in a more systematic way
        # Ending script tags are special since we can put profile data in JSON
        # embedded inside an HTML. Until we can fix that problem in the jsonify
        # code, we temporarily disallow these as a stop gap.
        new_name = new_name.replace('</script>', '')
        if new_name != self.user_nickname:
            if nickname and not nicknames.is_valid_nickname(nickname):
                # The user picked a name, and it seems offensive. Reject it.
                return False

            self.user_nickname = new_name
            def txn():
                NicknameIndex.update_indices(self)
                self.put()
            transaction_util.ensure_in_transaction(txn, xg_on=True)
        return True

    @property
    def email(self):
        """ Unlike key_email below, this email property
        represents the user's current email address and
        can be displayed to users.
        """
        return self.user_email

    @property
    def key_email(self):
        """ key_email is an unchanging key that's used
        as a reference to this user in many old db entities.
        It will never change, and it does not represent the user's
        actual email. It is used as a key for db queries only. It
        should not be displayed to users -- for that, use the 'email'
        property.
        """
        return self.user.email()

    @property
    def badge_counts(self):
        return badges.util_badges.get_badge_counts(self)

    @property
    def prettified_user_email(self):
        if self.is_facebook_user:
            return "_fb" + self.user_id[len(facebook_util.FACEBOOK_ID_PREFIX):]
        elif self.is_phantom:
            return "nouser"
        else:
            return "_em" + urllib.quote(self.user_email)

    @staticmethod
    def get_from_url_segment(segment):
        username_or_email = None

        if segment:
            segment = urllib.unquote(segment).decode('utf-8').strip()
            if segment.startswith("_fb"):
                username_or_email = segment.replace("_fb", facebook_util.FACEBOOK_ID_PREFIX)
            elif segment.startswith("_em"):
                username_or_email = segment.replace("_em", "")
            else:
                username_or_email = segment

        return UserData.get_from_username_or_email(username_or_email)

    @property
    def profile_root(self):
        root = "/profile/"

        if self.username:
            root += self.username
        else:
            root += self.prettified_user_email

        return root

    # Return data about the user that we'd like to track in MixPanel
    @staticmethod
    def get_analytics_properties(user_data):
        properties_list = []

        if not user_data:
            properties_list.append(("User Type", "New"))
        elif user_data.is_phantom:
            properties_list.append(("User Type", "Phantom"))
        else:
            properties_list.append(("User Type", "Logged In"))

        if user_data:
            properties_list.append(("User Points", user_data.points))
            properties_list.append(("User Videos", user_data.get_videos_completed()))
            properties_list.append(("User Exercises", len(user_data.all_proficient_exercises)))
            properties_list.append(("User Badges", len(user_data.badges)))
            properties_list.append(("User Video Time", user_data.total_seconds_watched))

        return properties_list

    @staticmethod
    @request_cache.cache()
    def current():
        user_id = util.get_current_user_id(bust_cache=True)
        email = user_id

        google_user = users.get_current_user()
        if google_user:
            email = google_user.email()

        if user_id:
            # Once we have rekeyed legacy entities,
            # we will be able to simplify this.
            return  UserData.get_from_user_id(user_id) or \
                    UserData.get_from_db_key_email(email) or \
                    UserData.insert_for(user_id, email)
        return None

    @staticmethod
    def pre_phantom():
        return UserData.insert_for(_PRE_PHANTOM_EMAIL, _PRE_PHANTOM_EMAIL)

    @property
    def is_facebook_user(self):
        return facebook_util.is_facebook_user_id(self.user_id)

    @property
    def is_phantom(self):
        return util.is_phantom_user(self.user_id)

    @property
    def is_demo(self):
        return self.user_email.startswith(_COACH_DEMO_COWORKER_EMAIL)

    @property
    def is_pre_phantom(self):
        return _PRE_PHANTOM_EMAIL == self.user_email

    @property
    def seconds_since_joined(self):
        return util.seconds_since(self.joined)

    @staticmethod
    @request_cache.cache_with_key_fxn(lambda user_id: "UserData_user_id:%s" % user_id)
    def get_from_user_id(user_id):
        if not user_id:
            return None

        query = UserData.all()
        query.filter('user_id =', user_id)
        query.order('-points') # Temporary workaround for issue 289

        return query.get()

    @staticmethod
    def get_from_user_input_email(email):
        if not email:
            return None

        query = UserData.all()
        query.filter('user_email =', email)
        query.order('-points') # Temporary workaround for issue 289

        return query.get()
    
    @staticmethod
    def get_all_for_user_input_email(email):
        if not email:
            return []

        query = UserData.all()
        query.filter('user_email =', email)
        return query

    @staticmethod
    def get_from_username(username):
        if not username:
            return None
        canonical_username = UniqueUsername.get_canonical(username)
        if not canonical_username:
            return None
        query = UserData.all()
        query.filter('username =', canonical_username.username)
        return query.get()

    @staticmethod
    def get_from_db_key_email(email):
        if not email:
            return None

        query = UserData.all()
        query.filter('user =', users.User(email))
        query.order('-points') # Temporary workaround for issue 289

        return query.get()

    @staticmethod
    def get_from_user(user):
        return UserData.get_from_db_key_email(user.email())

    @staticmethod
    def get_from_username_or_email(username_or_email):
        if not username_or_email:
            return None

        user_data = None

        if UniqueUsername.is_valid_username(username_or_email):
            user_data = UserData.get_from_username(username_or_email)
        else:
            user_data = UserData.get_possibly_current_user(username_or_email)

        return user_data

    # Avoid an extra DB call in the (fairly often) case that the requested email
    # is the email of the currently logged-in user
    @staticmethod
    def get_possibly_current_user(email):
        if not email:
            return None

        user_data_current = UserData.current()
        if user_data_current and user_data_current.user_email == email:
            return user_data_current
        return UserData.get_from_user_input_email(email) or UserData.get_from_user_id(email)

    @classmethod
    def key_for(cls, user_id):
        return "user_id_key_%s" % user_id

    @staticmethod
    def get_possibly_current_user_by_username(username):
        if not username:
            return None

        user_data_current = UserData.current()
        if user_data_current and user_data_current.username == username:
            return user_data_current

        return UserData.get_from_username(username)

    @staticmethod
    def insert_for(user_id, email, username=None, password=None, **kwds):
        """ Creates a user with the specified values, if possible, or returns
        an existing user if the user_id has been used by an existing user.
        
        Returns None if user_id or email values are invalid.

        """

        if not user_id or not email:
            return None

        # Make default dummy values for the ones that don't matter
        prop_values = {
            'moderator': False,
            'proficient_exercises': [],
            'suggested_exercises': [],
            'need_to_reassess': True,
            'points': 0,
            'coaches': [],
        }

        # Allow clients to override
        prop_values.update(**kwds)
        
        # Forcefully override with important items.
        user = users.User(email)
        key_name = UserData.key_for(user_id)
        for pname, pvalue in {
            'key_name': key_name,
            'user': user,
            'current_user': user,
            'user_id': user_id,
            'user_email': email,
            }.iteritems():
            if pname in prop_values:
                logging.warning("UserData creation about to override"
                                " specified [%s] value" % pname)
            prop_values[pname] = pvalue

        if username or password:
            # Username or passwords are separate entities.
            # That means we have to do this in multiple steps - make a txn.
            def create_txn():
                user_data = UserData.get_by_key_name(key_name)
                if user_data is None:
                    user_data = UserData(**prop_values)
                    # Both claim_username and set_password updates user_data
                    # and will call put() for us.
                    if username and not user_data.claim_username(username):
                        raise datastore_errors.Rollback("username [%s] already taken" % username)
                    if password and user_data.set_password(password):
                        raise datastore_errors.Rollback("invalid password for user")
                else:
                    logging.warning("Tried to re-make a user for key=[%s]" %
                                    key_name)
                return user_data

            xg_on = db.create_transaction_options(xg=True)
            user_data = db.run_in_transaction_options(xg_on, create_txn)

        else:
            # No username means we don't have to do manual transactions.
            # Note that get_or_insert is a transaction itself, and it can't
            # be nested in the above transaction.
            user_data = UserData.get_or_insert(**prop_values)

        if user_data and not user_data.is_phantom:
            # Record that we now have one more registered user
            if (datetime.datetime.now() - user_data.joined).seconds < 60:
                # Extra safety check against user_data.joined in case some
                # subtle bug results in lots of calls to insert_for for
                # UserData objects with existing key_names.
                user_counter.add(1)

        return user_data

    def consume_identity(self, new_user):
        """ Takes over another UserData's identity by updating this user's
        user_id, and other personal information with that of new_user's,
        assuming the new_user has never received any points.

        This is useful if this account is a phantom user with history
        and needs to be updated with a newly registered user's info, or some
        other similar situation.

        This method will fail if new_user has any points whatsoever,
        since we don't yet support migrating associated UserVideo
        and UserExercise objects.

        Returns whether or not the merge was successful.
        
        """
        
        if (new_user.points > 0):
            return False

        # Really important that we be mindful of people who have been added as
        # coaches - no good way to transfer that right now.
        if new_user.has_students():
            return False
    
        def txn():
            self.user_id = new_user.user_id
            self.current_user = new_user.current_user
            self.user_email = new_user.user_email
            self.user_nickname = new_user.user_nickname
            self.birthdate = new_user.birthdate
            self.gender = new_user.gender
            self.joined = new_user.joined
            if new_user.last_login:
                if self.last_login:
                    self.last_login = max(new_user.last_login, self.last_login)
                else:
                    self.last_login = new_user.last_login
            self.set_password_from_user(new_user)
            UniqueUsername.transfer(new_user, self)
            
            # TODO(benkomalo): update nickname and indices!
        
            if self.put():
                new_user.delete()
                return True
            return False

        result = transaction_util.ensure_in_transaction(txn, xg_on=True)
        if result:
            # Note that all of the updates to the above fields causes changes
            # to indices affected by each user. Since some of those are really
            # important (e.g. retrieving a user by user_id), it'd be dangerous
            # for a subsequent request to see stale indices. Force an apply()
            # of the HRD by doing a get()
            db.get(self.key())
            db.get(new_user.key())
        return result

    @staticmethod
    def get_visible_user(user, actor=None):
        """ Retrieve user for actor, in the style of O-Town, all or nothing.

        TODO(marcia): Sort out UserData and UserProfile visibility turf war
        """
        if actor is None:
            actor = UserData.current() or UserData.pre_phantom()

        if user and user.is_visible_to(actor):
            # Allow access to user's profile
            return user

        return None

    def delete(self):
        # Override delete(), so that we can log this severe event, and clean
        # up some statistics.
        logging.info("Deleting user data for %s with points %s" % (self.key_email, self.points))
        logging.info("Dumping user data for %s: %s" % (self.user_id, jsonify.jsonify(self)))

        if not self.is_phantom:
            user_counter.add(-1)
        
        # TODO(benkomalo): handle cleanup of nickname indices!

        # Delegate to the normal implentation
        super(UserData, self).delete()

    def is_certain_to_be_thirteen(self):
        """ A conservative check that guarantees a user is at least 13 years
        old based on their login type.

        Note that even if someone is over 13, this can return False, but if
        this returns True, they're guaranteed to be over 13.
        """

        # Normal Gmail accounts and FB accounts require users be at least 13yo.
        if self.birthdate:
            return age_util.get_age(self.birthdate) >= 13
            
        email = self.email
        return (email.endswith("@gmail.com")
                or email.endswith("@googlemail.com")  # Gmail in Germany
                or email.endswith("@khanacademy.org")  # We're special
                or self.developer  # Really little kids don't write software
                or facebook_util.is_facebook_user_id(email))

    def get_or_insert_exercise(self, exercise, allow_insert=True):
        # TODO(csilvers): get rid of the circular import here
        import exercise_models 

        if not exercise:
            return None

        exid = exercise.name
        userExercise = exercise_models.UserExercise.get_by_key_name(exid, parent=self)

        if not userExercise:
            # There are some old entities lying around that don't have keys.
            # We have to check for them here, but once we have reparented and rekeyed legacy entities,
            # this entire function can just be a call to .get_or_insert()
            query = exercise_models.UserExercise.all(keys_only=True)
            query.filter('user =', self.user)
            query.filter('exercise =', exid)
            query.order('-total_done') # Temporary workaround for issue 289

            # In order to guarantee consistency in the HR datastore, we need to query
            # via db.get for these old, parent-less entities.
            key_user_exercise = query.get()
            if key_user_exercise:
                userExercise = exercise_models.UserExercise.get(str(key_user_exercise))

        if allow_insert and not userExercise:
            userExercise = exercise_models.UserExercise.get_or_insert(
                key_name=exid,
                parent=self,
                user=self.user,
                exercise=exid,
                exercise_model=exercise,
                streak=0,
                _progress=0.0,
                longest_streak=0,
                first_done=datetime.datetime.now(),
                last_done=None,
                total_done=0,
                _accuracy_model=accuracy_model.AccuracyModel(),
                )

        return userExercise

    def reassess_from_graph(self, user_exercise_graph):
        all_proficient_exercises = user_exercise_graph.proficient_exercise_names()
        suggested_exercises = user_exercise_graph.suggested_exercise_names()

        is_changed = (all_proficient_exercises != self.all_proficient_exercises or
                      suggested_exercises != self.suggested_exercises)

        self.all_proficient_exercises = all_proficient_exercises
        self.suggested_exercises = suggested_exercises
        self.need_to_reassess = False

        return is_changed

    def reassess_if_necessary(self, user_exercise_graph=None):
        if not self.need_to_reassess or self.all_proficient_exercises is None:
            return False

        if user_exercise_graph is None:
            # TODO(csilvers): get rid of the circular import here
            import exercise_models 
            user_exercise_graph = exercise_models.UserExerciseGraph.get(self)

        return self.reassess_from_graph(user_exercise_graph)

    def is_proficient_at(self, exid, exgraph=None):
        self.reassess_if_necessary(exgraph)
        return (exid in self.all_proficient_exercises)

    def is_explicitly_proficient_at(self, exid):
        return (exid in self.proficient_exercises)

    def is_suggested(self, exid):
        self.reassess_if_necessary()
        return (exid in self.suggested_exercises)

    def get_coaches_data(self):
        """ Return list of coaches UserData.
        """
        coaches = []
        for key_email in self.coaches:
            user_data_coach = UserData.get_from_db_key_email(key_email)
            if user_data_coach:
                coaches.append(user_data_coach)
        return coaches

    def get_students_data(self):
        coach_email = self.key_email
        query = UserData.all().filter('coaches =', coach_email)
        students_data = [s for s in query.fetch(1000)]

        if coach_email.lower() != coach_email:
            students_set = set([s.key().id_or_name() for s in students_data])
            query = UserData.all().filter('coaches =', coach_email.lower())
            for student_data in query:
                if student_data.key().id_or_name() not in students_set:
                    students_data.append(student_data)
        return students_data

    def get_coworkers_data(self):
        return filter(lambda user_data: user_data is not None, \
                map(lambda coworker_email: UserData.get_from_db_key_email(coworker_email) , self.coworkers))

    def has_students(self):
        coach_email = self.key_email
        count = UserData.all().filter('coaches =', coach_email).count()

        if coach_email.lower() != coach_email:
            count += UserData.all().filter('coaches =', coach_email.lower()).count()

        return count > 0

    def remove_student_lists(self, removed_coach_emails):
        """ Remove student lists associated with removed coaches.
        """
        if len(removed_coach_emails):
            # Get the removed coaches' keys
            removed_coach_keys = frozenset([
                    UserData.get_from_username_or_email(coach_email).key()
                    for coach_email in removed_coach_emails])

            # Get the StudentLists from our list of StudentList keys
            student_lists = StudentList.get(self.student_lists)

            # Theoretically, a StudentList allows for multiple coaches,
            # but in practice there is exactly one coach per StudentList.
            # If/when we support multiple coaches per list, we would need to change
            # how this works... How *does* it work? Well, let me tell you.

            # Set our student_lists to all the keys of StudentLists
            # whose coaches do not include any removed coaches.
            self.student_lists = [l.key() for l in student_lists
                    if (len(frozenset(l.coaches) & removed_coach_keys) == 0)]

    def is_coached_by(self, user_data_coach):
        return user_data_coach.key_email in self.coaches or user_data_coach.key_email.lower() in self.coaches

    def is_coworker_of(self, user_data_coworker):
        return user_data_coworker.key_email in self.coworkers

    def is_coached_by_coworker_of_coach(self, user_data_coach):
        for coworker_email in user_data_coach.coworkers:
            if coworker_email in self.coaches:
                return True
        return False

    def is_administrator(self):
        # Only works for currently logged in user. Make sure there
        # is both a current user data and current user is an admin.
        user_data = UserData.current()
        return user_data and users.is_current_user_admin()

    def is_visible_to(self, user_data):
        """ Returns whether or not this user's information is *fully* visible
        to the specified user
        """
        return (self.key_email == user_data.key_email or self.is_coached_by(user_data)
                or self.is_coached_by_coworker_of_coach(user_data)
                or user_data.developer or user_data.is_administrator())

    def are_students_visible_to(self, user_data):
        return self.is_coworker_of(user_data) or user_data.developer or user_data.is_administrator()

    def record_activity(self, dt_activity):

        # Make sure last_activity and start_consecutive_activity_date have values
        self.last_activity = self.last_activity or dt_activity
        self.start_consecutive_activity_date = self.start_consecutive_activity_date or dt_activity

        if dt_activity > self.last_activity:

            # If it has been over 40 hours since we last saw this user, restart
            # the consecutive activity streak.
            #
            # We allow for a lenient 40 hours in order to offer kinder timezone
            # interpretation.
            #
            # 36 hours wasn't quite enough. A user with activity at 8am on
            # Monday and 8:15pm on Tuesday would not have consecutive days of
            # activity.
            #
            # See http://meta.stackoverflow.com/questions/55483/proposed-consecutive-days-badge-tracking-change
            if util.hours_between(self.last_activity, dt_activity) >= 40:
                self.start_consecutive_activity_date = dt_activity

            self.last_activity = dt_activity

    def current_consecutive_activity_days(self):
        if not self.last_activity or not self.start_consecutive_activity_date:
            return 0

        dt_now = datetime.datetime.now()

        # If it has been over 40 hours since last activity, bail.
        if util.hours_between(self.last_activity, dt_now) >= 40:
            return 0

        return (self.last_activity - self.start_consecutive_activity_date).days

    def add_points(self, points):
        if self.points is None:
            self.points = 0

        if not hasattr(self, "_original_points"):
            self._original_points = self.points

        # Check if we crossed an interval of 2500 points
        if self.points % 2500 > (self.points + points) % 2500:
            phantom_users.util_notify.update(self, user_exercise=None, threshold=True)
        self.points += points

    def original_points(self):
        return getattr(self, "_original_points", 0)

    def get_videos_completed(self):
        if self.videos_completed < 0:
            # TODO(csilvers): get rid of the circular import here
            import video_models
            self.videos_completed = video_models.UserVideo.count_completed_for_user_data(self)
            self.put()
        return self.videos_completed

    def feedback_notification_count(self):
        if self.count_feedback_notification == -1:
            self.count_feedback_notification = models_discussion.FeedbackNotification.gql("WHERE user = :1", self.user).count()
            self.put()
        return self.count_feedback_notification

    def save_goal(self, goal):
        '''save a goal, atomically updating the user_data.has_current_goal when
        necessary'''

        if self.has_current_goals: # no transaction necessary
            goal.put()
            return

        # otherwise this is the first goal the user has created, so be sure we
        # update user_data.has_current_goals too
        def save_goal():
            self.has_current_goals = True
            db.put([self, goal])
        db.run_in_transaction(save_goal)

    def claim_username(self, name, clock=None):
        """ Claims a username for the current user, and assigns it to her
        atomically. Returns True on success.
        """
        def claim_and_set():
            claim_success = UniqueUsername._claim_internal(name,
                                                           claimer_id=self.user_id,
                                                           clock=clock)
            if claim_success:
                if self.username:
                    UniqueUsername.release(self.username, clock)
                self.username = name
                self.put()
            return claim_success
        
        result = transaction_util.ensure_in_transaction(claim_and_set, xg_on=True)
        if result:
            # Success! Ensure we flush the apply() phase of the modifications
            # so that subsequent queries get consistent results. This makes
            # claiming usernames slightly slower, but safer since rapid
            # claiming or rapid claim/read won't result in weirdness.
            db.get([self.key()])
        return result

    def has_password(self):
        return self.credential_version is not None

    def has_public_profile(self):
        return (self.is_profile_public
                and self.username is not None
                and len(self.username) > 0)

    def __unicode__(self):
        return "<UserData [%s] [%s] [%s]>" % (self.user_id,
                                              self.email,
                                              self.username or "<no username>")

    @classmethod
    def from_json(cls, json, user=None):
        """This method exists for testing convenience only. It's called only
        by code that runs in exclusively in development mode. Do not rely on
        this method in production code. If you need to break this code to
        implement some new feature, feel free!
        """
        user_id = json['user_id']
        email = json['email']
        user = user or users.User(email)

        user_data = cls(
            key_name=cls.key_for(user_id),
            user=user,
            current_user=user,
            user_id=user_id,
            user_email=email,
            moderator=False,
            joined=util.parse_iso8601(json['joined']),
            last_activity=util.parse_iso8601(json['last_activity']),
            last_badge_review=util.parse_iso8601(json['last_badge_review']),
            start_consecutive_activity_date=util.parse_iso8601(json['start_consecutive_activity_date']),
            need_to_reassess=True,
            points=int(json['points']),
            nickname=json['nickname'],
            coaches=['test@example.com'],
            total_seconds_watched=int(json['total_seconds_watched']),
            all_proficient_exercises=json['all_proficient_exercises'],
            proficient_exercises=json['proficient_exercises'],
            suggested_exercises=json['suggested_exercises'],
        )
        return user_data


class UniqueUsername(db.Model):
    """Stores usernames that users have set from their profile page."""
    # The username value selected by the user.
    username = db.StringProperty()

    # A date indicating when the username was released.
    # This is useful to block off usernames, particularly after they were just
    # released, so they can be put in a holding period.
    # This will be set to an "infinitely" far-futures date while the username
    # is in use
    release_date = db.DateTimeProperty()

    # The user_id value of the UserData that claimed this username.
    # NOTE - may be None for some old UniqueUsername objects, or if it was
    # just blocked off for development.
    claimer_id = db.StringProperty()

    @staticmethod
    def build_key_name(username):
        """ Builds a unique, canonical version of a username. """
        if username is None:
            logging.error("Trying to build a key_name for a null username!")
            return ""
        return username.replace('.', '').lower()

    # Usernames must be at least 3 characters long (excluding periods), must
    # start with a letter
    VALID_KEY_NAME_RE = re.compile('^[a-z][a-z0-9]{2,}$')

    @staticmethod
    def is_username_too_short(username, key_name=None):
        if key_name is None:
            key_name = UniqueUsername.build_key_name(username)
        return len(key_name) < 3

    @staticmethod
    def is_valid_username(username, key_name=None):
        """ Determines if a candidate for a username is valid
        according to the limitations we enforce on usernames.

        Usernames must be at least 3 characters long (excluding dots), start
        with a letter and be alphanumeric (ascii only).
        """
        if username.startswith('.'):
            return False
        if key_name is None:
            key_name = UniqueUsername.build_key_name(username)
        return UniqueUsername.VALID_KEY_NAME_RE.match(key_name) is not None

    @staticmethod
    def is_available_username(username, key_name=None, clock=None):
        if key_name is None:
            key_name = UniqueUsername.build_key_name(username)
        entity = UniqueUsername.get_by_key_name(key_name)
        if clock is None:
            clock = datetime.datetime
        return entity is None or not entity._is_in_holding(clock.utcnow())

    def _is_in_holding(self, utcnow):
        return self.release_date + UniqueUsername.HOLDING_PERIOD_DELTA >= utcnow

    INFINITELY_FAR_FUTURE = datetime.datetime(9999, 1, 1, 0, 0, 0)

    # Released usernames are held for 120 days
    HOLDING_PERIOD_DELTA = datetime.timedelta(120)

    @staticmethod
    def _claim_internal(desired_name, claimer_id=None, clock=None):
        key_name = UniqueUsername.build_key_name(desired_name)
        if not UniqueUsername.is_valid_username(desired_name, key_name):
            return False

        is_available = UniqueUsername.is_available_username(
                desired_name, key_name, clock)
        if is_available:
            entity = UniqueUsername(key_name=key_name)
            entity.username = desired_name
            entity.release_date = UniqueUsername.INFINITELY_FAR_FUTURE
            entity.claimer_id = claimer_id
            entity.put()
        return is_available

    @staticmethod
    def claim(desired_name, claimer_id=None, clock=None):
        """ Claim an unclaimed username.

        Return True on success, False if you are a slow turtle or invalid.
        See is_valid_username for limitations of a username.

        """

        key_name = UniqueUsername.build_key_name(desired_name)
        if not UniqueUsername.is_valid_username(desired_name, key_name):
            return False

        return db.run_in_transaction(UniqueUsername._claim_internal,
                                     desired_name,
                                     claimer_id,
                                     clock)

    @staticmethod
    def release(username, clock=None):
        if clock is None:
            clock = datetime.datetime

        if username is None:
            logging.error("Trying to release a null username!")
            return

        entity = UniqueUsername.get_canonical(username)
        if entity is None:
            logging.warn("Releasing username %s that doesn't exist" % username)
            return
        entity.release_date = clock.utcnow()
        entity.put()
        
    @staticmethod
    def transfer(from_user, to_user):
        """ Transfers a username from one user to another, assuming the to_user
        does not already have a username.
        
        Returns whether or not a transfer occurred.

        """
        def txn():
            if not from_user.username or to_user.username:
                return False
            entity = UniqueUsername.get_canonical(from_user.username)
            entity.claimer_id = to_user.user_id
            to_user.username = from_user.username
            from_user.username = None
            db.put([from_user, to_user, entity])
            return True
        return transaction_util.ensure_in_transaction(txn, xg_on=True)

    @staticmethod
    def get_canonical(username):
        """ Returns the entity with the canonical format of the user name, as
        it was originally claimed by the user, given a string that may include
        more or less period characters in it.
        e.g. "joe.smith" may actually translate to "joesmith"
        """
        key_name = UniqueUsername.build_key_name(username)
        return UniqueUsername.get_by_key_name(key_name)


class NicknameIndex(db.Model):
    """ Index entries to be able to search users by their nicknames.

    Each user may have multiple index entries, all pointing to the same user.
    These entries are expected to be direct children of UserData entities.

    These are created for fast user searches.
    """

    # The index string that queries can be matched again. Must be built out
    # using nicknames.build_index_strings
    index_value = db.StringProperty()

    @staticmethod
    def update_indices(user):
        """ Updates the indices for a user given her current nickname. """
        nickname = user.nickname
        index_strings = nicknames.build_index_strings(nickname)

        db.delete(NicknameIndex.entries_for_user(user))
        entries = [NicknameIndex(parent=user, index_value=s)
                   for s in index_strings]
        db.put(entries)

    @staticmethod
    def entries_for_user(user):
        """ Retrieves all index entries for a given user. """
        q = NicknameIndex.all()
        q.ancestor(user)
        return q.fetch(10000)

    @staticmethod
    def users_for_search(raw_query):
        """ Given a raw query string, retrieve a list of the users that match
        that query by returning a list of their entity's key values.

        The values are guaranteed to be unique.

        TODO: there is no ranking among the result set, yet
        TODO: extend API so that the query can have an optional single token
              that can be prefixed matched, for autocomplete purposes
        """

        q = NicknameIndex.all()
        q.filter("index_value =", nicknames.build_search_query(raw_query))
        return list(set([entry.parent_key() for entry in q]))


class UnverifiedUser(db.Model):
    """ Preliminary signup data for new users.

    Includes an e-mail address that needs to be verified.
    """
    
    email = db.StringProperty()
    birthdate = db.DateProperty(indexed=False)

    # used as a token sent in an e-mail verification link.
    randstring = db.StringProperty(indexed=True)
    
    @staticmethod
    def get_or_insert_for_value(email, birthdate):
        return UnverifiedUser.get_or_insert(
                key_name=email,
                email=email,
                birthdate=birthdate,
                randstring=os.urandom(20).encode("hex"))

    @staticmethod
    def get_for_value(email):
        # Email is also used as the db key
        return UnverifiedUser.get_by_key_name(email)

    @staticmethod
    def get_for_token(token):
        return UnverifiedUser.all().filter("randstring =", token).get()


# TODO(csilvers): move this away from user_models (into some
# coach-related models file?) once we can remove the circular
# dependency between StudentList and UserData.
class StudentList(db.Model):
    """A list of students associated with a single coach."""
    name = db.StringProperty()
    coaches = db.ListProperty(db.Key)

    def delete(self, *args, **kwargs):
        self.remove_all_students()
        db.Model.delete(self, *args, **kwargs)

    def remove_all_students(self):
        students = self.get_students_data()
        for s in students:
            s.student_lists.remove(self.key())
        db.put(students)

    @property
    def students(self):
        return UserData.all().filter("student_lists = ", self.key())

    # these methods have the same interface as the methods on UserData
    def get_students_data(self):
        return [s for s in self.students]

    @staticmethod
    def get_for_coach(key):
        query = StudentList.all()
        query.filter("coaches = ", key)
        return query
