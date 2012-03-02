import re
import os
import hashlib
import urllib

from google.appengine.ext import db
from google.appengine.ext import deferred

import datetime
import models
import request_handler
import user_util
import points
import layer_cache
import knowledgemap
import string
import simplejson as json
from badges import util_badges, last_action_cache
from phantom_users import util_notify
from custom_exceptions import MissingExerciseException, QuietException
from api.auth.xsrf import ensure_xsrf_cookie
from api import jsonify
from gae_bingo.gae_bingo import bingo, ab_test
from gae_bingo.models import ConversionTypes
from goals.models import GoalList
from experiments import StrugglingExperiment
from js_css_packages import templatetags
from exercises.handlers import ViewExercise

class MoveMapNodes(request_handler.RequestHandler):
    def post(self):
        self.get()

    @user_util.developer_only
    def get(self):
        node_list = string.split(self.request_string('exercises'), ',')
        delta_h = self.request_int('delta_h')
        delta_v = self.request_int('delta_v')

        for node_id in node_list:
            exercise = models.Exercise.get_by_name(node_id)

            exercise.h_position += delta_h
            exercise.v_position += delta_v

            exercise.put()

# TODO(kamens): once all edge-case logic is moved out of OldViewExercise piece-by-piece into 
# exercises.handlers.ViewExercise, this should be removed.
class OldViewExercise(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, exid=None):

        # TODO(david): Is there some webapp2 magic that will allow me not to
        #     repeat this URL string in main.py?
        review_mode = self.request.path == "/review" 

        if not exid and not review_mode:
            self.redirect("/exercise/%s" % self.request_string("exid", default="addition_1"))
            return

        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        if review_mode:
            # Take the first review exercise if available
            exid = (user_exercise_graph.review_exercise_names() or
                    user_exercise_graph.proficient_exercise_names() or
                    ["addition_1"])[0]
            reviews_left_count = user_exercise_graph.reviews_left_count()

        exercise = models.Exercise.get_by_name(exid)

        if not exercise:
            raise MissingExerciseException("Missing exercise w/ exid '%s'" % exid)

        user_exercise = user_data.get_or_insert_exercise(exercise)

        # Cache these so we don't have to worry about future lookups
        user_exercise.exercise_model = exercise
        user_exercise._user_data = user_data
        user_exercise._user_exercise_graph = user_exercise_graph
        user_exercise.summative = exercise.summative

        # Temporarily work around in-app memory caching bug
        exercise.user_exercise = None

        problem_number = self.request_int('problem_number', default=(user_exercise.total_done + 1))

        user_data_student = self.request_student_user_data(legacy=True) or user_data
        if user_data_student.key_email != user_data.key_email and not user_data_student.is_visible_to(user_data):
            user_data_student = user_data

        viewing_other = user_data_student.key_email != user_data.key_email

        # Can't view your own problems ahead of schedule
        if not viewing_other and problem_number > user_exercise.total_done + 1:
            problem_number = user_exercise.total_done + 1

        # When viewing another student's problem or a problem out-of-order, show read-only view
        read_only = viewing_other or problem_number != (user_exercise.total_done + 1)

        exercise_template_html = exercise_template()

        exercise_body_html, exercise_inline_script, exercise_inline_style, data_require, sha1 = exercise_contents(exercise)
        user_exercise.exercise_model.sha1 = sha1

        user_exercise.exercise_model.related_videos = map(lambda exercise_video: exercise_video.video, user_exercise.exercise_model.related_videos_fetch())
        for video in user_exercise.exercise_model.related_videos:
            video.id = video.key().id()

        renderable = True

        if read_only:
            # Override current problem number and user being inspected
            # so proper exercise content will be generated
            user_exercise.total_done = problem_number - 1
            user_exercise.user = user_data_student.user
            user_exercise.read_only = True

            if not self.request_bool("renderable", True):
                # We cannot render old problems that were created in the v1 exercise framework.
                renderable = False

            query = models.ProblemLog.all()
            query.filter("user = ", user_data_student.user)
            query.filter("exercise = ", exid)

            # adding this ordering to ensure that query is served by an existing index.
            # could be ok if we remove this
            query.order('time_done')
            problem_logs = query.fetch(500)

            problem_log = None
            for p in problem_logs:
                if p.problem_number == problem_number:
                    problem_log = p
                    break

            user_activity = []
            previous_time = 0

            if not problem_log or not hasattr(problem_log, "hint_after_attempt_list"):
                renderable = False
            else:
                # Don't include incomplete information
                problem_log.hint_after_attempt_list = filter(lambda x: x != -1, problem_log.hint_after_attempt_list)

                while len(problem_log.hint_after_attempt_list) and problem_log.hint_after_attempt_list[0] == 0:
                    user_activity.append([
                        "hint-activity",
                        "0",
                        max(0, problem_log.hint_time_taken_list[0] - previous_time)
                        ])

                    previous_time = problem_log.hint_time_taken_list[0]
                    problem_log.hint_after_attempt_list.pop(0)
                    problem_log.hint_time_taken_list.pop(0)

                # For each attempt, add it to the list and then add any hints
                # that came after it
                for i in range(0, len(problem_log.attempts)):
                    user_activity.append([
                        "correct-activity" if problem_log.correct else "incorrect-activity",
                        unicode(problem_log.attempts[i] if problem_log.attempts[i] else 0),
                        max(0, problem_log.time_taken_attempts[i] - previous_time)
                        ])

                    previous_time = 0

                    # Here i is 0-indexed but problems are numbered starting at 1
                    while (len(problem_log.hint_after_attempt_list) and
                            problem_log.hint_after_attempt_list[0] == i + 1):
                        user_activity.append([
                            "hint-activity",
                            "0",
                            max(0, problem_log.hint_time_taken_list[0] - previous_time)
                            ])

                        previous_time = problem_log.hint_time_taken_list[0]
                        # easiest to just pop these instead of maintaining
                        # another index into this list
                        problem_log.hint_after_attempt_list.pop(0)
                        problem_log.hint_time_taken_list.pop(0)

                user_exercise.user_activity = user_activity

                if problem_log.count_hints is not None:
                    user_exercise.count_hints = problem_log.count_hints

                user_exercise.current = problem_log.sha1 == sha1
        else:
            # Not read_only
            suggested_exercise_names = user_exercise_graph.suggested_exercise_names()
            if exercise.name in suggested_exercise_names:
                bingo('suggested_activity_visit_suggested_exercise')

        is_webos = self.is_webos()
        browser_disabled = is_webos or self.is_older_ie()
        renderable = renderable and not browser_disabled

        url_pattern = "/exercise/%s?student_email=%s&problem_number=%d"
        user_exercise.previous_problem_url = url_pattern % \
            (exid, user_data_student.key_email, problem_number - 1)
        user_exercise.next_problem_url = url_pattern % \
            (exid, user_data_student.key_email, problem_number + 1)

        user_exercise_json = jsonify.jsonify(user_exercise)

        template_values = {
            'exercise': exercise,
            'user_exercise_json': user_exercise_json,
            'exercise_body_html': exercise_body_html,
            'exercise_template_html': exercise_template_html,
            'exercise_inline_script': exercise_inline_script,
            'exercise_inline_style': exercise_inline_style,
            'data_require': data_require,
            'read_only': read_only,
            'selected_nav_link': 'practice',
            'browser_disabled': browser_disabled,
            'is_webos': is_webos,
            'renderable': renderable,
            'issue_labels': ('Component-Code,Exercise-%s,Problem-%s' % (exid, problem_number)),
            'reviews_left_count': reviews_left_count if review_mode else "null",
        }

        self.render_jinja2_template("exercise_template.html", template_values)

def exercise_graph_dict_json(user_data, admin=False):
    user_exercise_graph = models.UserExerciseGraph.get(user_data)
    if user_data.reassess_from_graph(user_exercise_graph):
        user_data.put()

    graph_dicts = user_exercise_graph.graph_dicts()
    if admin:
        suggested_graph_dicts = []
        proficient_graph_dicts = []
        recent_graph_dicts = []
        review_graph_dicts = []
    else:
        suggested_graph_dicts = user_exercise_graph.suggested_graph_dicts()
        proficient_graph_dicts = user_exercise_graph.proficient_graph_dicts()
        recent_graph_dicts = user_exercise_graph.recent_graph_dicts()
        review_graph_dicts = user_exercise_graph.review_graph_dicts()

    for graph_dict in suggested_graph_dicts:
        graph_dict["status"] = "Suggested"

    for graph_dict in proficient_graph_dicts:
        graph_dict["status"] = "Proficient"

    for graph_dict in recent_graph_dicts:
        graph_dict["recent"] = True

    for graph_dict in review_graph_dicts:
        graph_dict["status"] = "Review"

        try:
            suggested_graph_dicts.remove(graph_dict)
        except ValueError:
            pass

    goal_exercises = GoalList.exercises_in_current_goals(user_data)

    graph_dict_data = []
    for graph_dict in graph_dicts:
        row = {
            'name': graph_dict["name"],
            'points': graph_dict.get("points", ''),
            'display_name': graph_dict["display_name"],
            'status': graph_dict.get("status"),
            'recent': graph_dict.get("recent", False),
            'progress': graph_dict["progress"],
            'progress_display': models.UserExercise.to_progress_display(graph_dict["progress"]),
            'longest_streak': graph_dict["longest_streak"],
            'h_position': graph_dict["h_position"],
            'v_position': graph_dict["v_position"],
            'summative': graph_dict["summative"],
            'num_milestones': graph_dict.get("num_milestones", 0),
            'goal_req': (graph_dict["name"] in goal_exercises),

            # get_by_name returns only exercises visible to current user
            'prereqs': [prereq["name"] for prereq in graph_dict["prerequisites"] if models.Exercise.get_by_name(prereq["name"])],
        }

        if admin:
            exercise = models.Exercise.get_by_name(graph_dict["name"])
            row["live"] = exercise and exercise.live
        graph_dict_data.append(row)

    return json.dumps(graph_dict_data)

class ViewAllExercises(request_handler.RequestHandler):

    def get(self):
        user_data = models.UserData.current() or models.UserData.pre_phantom()
        user_exercise_graph = models.UserExerciseGraph.get(user_data)

        show_review_drawer = (not user_exercise_graph.has_completed_review())

        template_values = {
            'graph_dict_data': exercise_graph_dict_json(user_data),
            'user_data': user_data,
            'expanded_all_exercises': user_data.expanded_all_exercises,
            'map_coords': json.dumps(knowledgemap.deserializeMapCoords(user_data.map_coords)),
            'selected_nav_link': 'practice',
            'show_review_drawer': show_review_drawer,
        }

        if show_review_drawer:
            template_values['review_statement'] = 'Attain mastery'
            template_values['review_call_to_action'] = "I'll do it"

        bingo('suggested_activity_exercises_landing')

        self.render_jinja2_template('viewexercises.html', template_values)

class RawExercise(request_handler.RequestHandler):
    def get(self):
        path = self.request.path
        exercise_file = urllib.unquote(path.rpartition('/')[2])
        self.response.headers["Content-Type"] = "text/html"
        self.response.out.write(raw_exercise_contents(exercise_file))

# TODO(kamens): hoping this whole thing will go away due to power mode
@layer_cache.cache(layer=layer_cache.Layers.InAppMemory)
def exercise_template():
    path = os.path.join(os.path.dirname(__file__), "../khan-exercises/exercises/khan-exercise.html")

    contents = ""
    f = open(path)

    if f:
        try:
            contents = f.read()
        finally:
            f.close()

    if not len(contents):
        raise MissingExerciseException("Missing exercise template")

    return contents

# TODO(kamens): hoping this whole thing will go away due to power mode
@layer_cache.cache_with_key_fxn(lambda exercise: "exercise_contents_%s" % exercise.name, layer=layer_cache.Layers.InAppMemory)
def exercise_contents(exercise):
    contents = raw_exercise_contents("%s.html" % exercise.name)

    re_data_require = re.compile("<html[^>]*(data-require=\".*?\")[^>]*>",
        re.DOTALL)
    match_data_require = re_data_require.search(contents)
    data_require = match_data_require.groups()[0] if match_data_require else ""

    re_body_contents = re.compile("<body>(.*)</body>", re.DOTALL)
    match_body_contents = re_body_contents.search(contents)
    body_contents = match_body_contents.groups()[0]

    re_script_contents = re.compile("<script[^>]*>(.*?)</script>", re.DOTALL)
    list_script_contents = re_script_contents.findall(contents)
    script_contents = ";".join(list_script_contents)

    re_style_contents = re.compile("<style[^>]*>(.*?)</style>", re.DOTALL)
    list_style_contents = re_style_contents.findall(contents)
    style_contents = "\n".join(list_style_contents)

    sha1 = hashlib.sha1(contents).hexdigest()

    if not len(body_contents):
        raise MissingExerciseException("Missing exercise body in content for exid '%s'" % exercise.name)

    result = map(lambda s: s.decode('utf-8'), (body_contents, script_contents,
        style_contents, data_require, sha1))

    if templatetags.use_compressed_packages():
        return result
    else:
        return layer_cache.UncachedResult(result)

@layer_cache.cache_with_key_fxn(lambda exercise_file: "exercise_raw_html_%s" % exercise_file, layer=layer_cache.Layers.InAppMemory)
def raw_exercise_contents(exercise_file):
    if templatetags.use_compressed_packages():
        exercises_dir = "../khan-exercises/exercises-packed"
        safe_to_cache = True
    else:
        exercises_dir = "../khan-exercises/exercises"
        safe_to_cache = False

    path = os.path.join(os.path.dirname(__file__), "%s/%s" % (exercises_dir, exercise_file))

    f = None
    contents = ""

    try:
        f = open(path)
        contents = f.read()
    except:
        raise MissingExerciseException(
                "Missing exercise file for exid '%s'" % exercise_file)
    finally:
        if f:
            f.close()

    if not len(contents):
        raise MissingExerciseException(
                "Missing exercise content for exid '%s'" % exercise_file)

    if safe_to_cache:
        return contents
    else:
        # we are displaying an unpacked exercise, either locally or in prod
        # with a querystring override. It's unsafe to cache this.
        return layer_cache.UncachedResult(contents)

def make_wrong_attempt(user_data, user_exercise):
    if user_exercise and user_exercise.belongs_to(user_data):
        user_exercise.update_proficiency_model(correct=False)
        user_exercise.put()

        return user_exercise

def attempt_problem(user_data, user_exercise, problem_number, attempt_number,
    attempt_content, sha1, seed, completed, count_hints, time_taken,
    review_mode, exercise_non_summative, problem_type, ip_address):

    if user_exercise and user_exercise.belongs_to(user_data):
        dt_now = datetime.datetime.now()
        exercise = user_exercise.exercise_model

        old_graph = user_exercise.get_user_exercise_graph()

        user_exercise.last_done = dt_now
        user_exercise.seconds_per_fast_problem = exercise.seconds_per_fast_problem
        user_exercise.summative = exercise.summative

        user_data.record_activity(user_exercise.last_done)

        # If a non-admin tries to answer a problem out-of-order, just ignore it
        # STOPSHIP TODO(kamens): re-enable this safety check once we get
        # data passed around and maintained properly
        if False and problem_number != user_exercise.total_done + 1 and not user_util.is_current_user_developer():
            # Only admins can answer problems out of order.
            raise QuietException("Problem number out of order (%s vs %s) for user_id: %s submitting attempt content: %s with seed: %s" % (problem_number, user_exercise.total_done + 1, user_data.user_id, attempt_content, seed))

        if len(sha1) <= 0:
            raise Exception("Missing sha1 hash of problem content.")

        if len(seed) <= 0:
            raise Exception("Missing seed for problem content.")

        if len(attempt_content) > 500:
            raise Exception("Attempt content exceeded maximum length.")

        # Build up problem log for deferred put
        problem_log = models.ProblemLog(
                key_name=models.ProblemLog.key_for(user_data, user_exercise.exercise, problem_number),
                user=user_data.user,
                exercise=user_exercise.exercise,
                problem_number=problem_number,
                time_taken=time_taken,
                time_done=dt_now,
                count_hints=count_hints,
                hint_used=count_hints > 0,
                correct=completed and not count_hints and (attempt_number == 1),
                sha1=sha1,
                seed=seed,
                problem_type=problem_type,
                count_attempts=attempt_number,
                attempts=[attempt_content],
                ip_address=ip_address,
                review_mode=review_mode,
        )

        if exercise.summative:
            problem_log.exercise_non_summative = exercise_non_summative

        first_response = (attempt_number == 1 and count_hints == 0) or (count_hints == 1 and attempt_number == 0)

        if user_exercise.total_done > 0 and user_exercise.streak == 0 and first_response:
            bingo('hints_keep_going_after_wrong')

        just_earned_proficiency = False

        # Users can only attempt problems for themselves, so the experiment
        # bucket always corresponds to the one for this current user
        struggling_model = StrugglingExperiment.get_alternative_for_user(
                 user_data, current_user=True) or StrugglingExperiment.DEFAULT
        if completed:

            user_exercise.total_done += 1

            if problem_log.correct:

                proficient = user_data.is_proficient_at(user_exercise.exercise)
                explicitly_proficient = user_data.is_explicitly_proficient_at(user_exercise.exercise)
                suggested = user_data.is_suggested(user_exercise.exercise)
                problem_log.suggested = suggested

                problem_log.points_earned = points.ExercisePointCalculator(user_exercise, suggested, proficient)
                user_data.add_points(problem_log.points_earned)

                # Streak only increments if problem was solved correctly (on first attempt)
                user_exercise.total_correct += 1
                user_exercise.streak += 1
                user_exercise.longest_streak = max(user_exercise.longest_streak, user_exercise.streak)

                user_exercise.update_proficiency_model(correct=True)

                bingo([
                    'struggling_problems_correct',
                    'suggested_activity_problems_correct',
                ])

                if user_exercise.progress >= 1.0 and not explicitly_proficient:
                    bingo([
                        'hints_gained_proficiency_all',
                        'struggling_gained_proficiency_all',
                        'suggested_activity_gained_proficiency_all',
                    ])
                    if not user_exercise.has_been_proficient():
                        bingo('hints_gained_new_proficiency')

                    if user_exercise.history_indicates_struggling(struggling_model):
                        bingo('struggling_gained_proficiency_post_struggling')

                    user_exercise.set_proficient(user_data)
                    user_data.reassess_if_necessary()

                    just_earned_proficiency = True
                    problem_log.earned_proficiency = True

            util_badges.update_with_user_exercise(
                user_data,
                user_exercise,
                include_other_badges=True,
                action_cache=last_action_cache.LastActionCache.get_cache_and_push_problem_log(user_data, problem_log))

            # Update phantom user notifications
            util_notify.update(user_data, user_exercise)

            bingo([
                'hints_problems_done',
                'struggling_problems_done',
                'suggested_activity_problems_done',
            ])

        else:
            # Only count wrong answer at most once per problem
            if first_response:
                user_exercise.update_proficiency_model(correct=False)
                bingo([
                    'hints_wrong_problems',
                    'struggling_problems_wrong',
                    'suggested_activity_problems_wrong',
                ])

            if user_exercise.is_struggling(struggling_model):
                bingo('struggling_struggled_binary')

        # If this is the first attempt, update review schedule appropriately
        if attempt_number == 1:
            user_exercise.schedule_review(completed)

        user_exercise_graph = models.UserExerciseGraph.get_and_update(user_data, user_exercise)

        goals_updated = GoalList.update_goals(user_data,
            lambda goal: goal.just_did_exercise(user_data, user_exercise,
                just_earned_proficiency))

        # Bulk put
        db.put([user_data, user_exercise, user_exercise_graph.cache])

        # Defer the put of ProblemLog for now, as we think it might be causing hot tablets
        # and want to shift it off to an automatically-retrying task queue.
        # http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
        deferred.defer(models.commit_problem_log, problem_log,
                       _queue="problem-log-queue",
                       _url="/_ah/queue/deferred_problemlog")

        if user_data is not None and user_data.coaches:
            # Making a separate queue for the log summaries so we can clearly see how much they are getting used
            deferred.defer(models.commit_log_summary_coaches, problem_log, user_data.coaches,
                       _queue="log-summary-queue",
                       _url="/_ah/queue/deferred_log_summary")

        return user_exercise, user_exercise_graph, goals_updated

class ExerciseAdmin(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        user_data = models.UserData.current()
        user_exercise_graph = models.UserExerciseGraph.current()

        if user_data.reassess_from_graph(user_exercise_graph):
            user_data.put()

        graph_dicts = user_exercise_graph.graph_dicts()
        for graph_dict in graph_dicts:
            exercise = models.Exercise.get_by_name(graph_dict["name"])
            graph_dict["live"] = exercise and exercise.live

        template_values = {
            'graph_dict_data': exercise_graph_dict_json(user_data, admin=True),
            'map_coords': knowledgemap.deserializeMapCoords(),
            }

        self.render_jinja2_template('exerciseadmin.html', template_values)

class EditExercise(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        exercise_name = self.request.get('name')
        if exercise_name:
            query = models.Exercise.all().order('name')
            exercises = query.fetch(1000)

            main_exercise = None
            for exercise in exercises:
                if exercise.name == exercise_name:
                    main_exercise = exercise


            exercise_videos = main_exercise.related_videos_query().fetch(50)

            template_values = {
                'exercises': exercises,
                'exercise_videos': exercise_videos,
                'main_exercise': main_exercise,
                'saved': self.request_bool('saved', default=False),
                }

            self.render_jinja2_template("editexercise.html", template_values)

class UpdateExercise(request_handler.RequestHandler):
    
    @staticmethod
    def do_update(dict):
        user = models.UserData.current().user

        exercise_name = dict["name"]

        query = models.Exercise.all()
        query.filter('name =', exercise_name)
        exercise = query.get()
        if not exercise:
            exercise = models.Exercise(name=exercise_name)
            exercise.prerequisites = []
            exercise.covers = []
            exercise.author = user
            exercise.summative = dict["summative"]

        exercise.prerequisites = dict["prerequisites"] 
        exercise.covers = dict["covers"]

        if "v_position" in dict:
            exercise.v_position = int(dict["v_position"])

        if "h_position" in dict:
            exercise.h_position = int(dict["h_position"])

        if "short_display_name" in dict:
            exercise.short_display_name = dict["short_display_name"]

        exercise.live = dict["live"]

        exercise.put()

        if "related_videos" in dict:
            UpdateExercise.do_update_related_videos(exercise, 
                                                    dict["related_videos"])
        elif "related_video_keys" in dict:
            UpdateExercise.do_update_related_video_keys(exercise, 
                                                    dict["related_video_keys"])
        else:
            UpdateExercise.do_update_related_video_keys(exercise, [])

        return exercise

    @staticmethod
    def do_update_related_videos(exercise, related_videos):
        video_keys = []
        for video_name in related_videos:
            video = models.Video.get_for_readable_id(video_name)
            if video and not video.key() in video_keys:
                video_keys.append(str(video.key()))

        UpdateExercise.do_update_related_video_keys(exercise, video_keys)

    @staticmethod
    def do_update_related_video_keys(exercise, video_keys):
        query = models.ExerciseVideo.all()
        query.filter('exercise =', exercise.key())
        existing_exercise_videos = query.fetch(1000)

        existing_video_keys = []
        for exercise_video in existing_exercise_videos:
            existing_video_keys.append(exercise_video.video.key())
            if not exercise_video.video.key() in video_keys:
                exercise_video.delete()

        for video_key in video_keys:
            if not video_key in existing_video_keys:
                exercise_video = models.ExerciseVideo()
                exercise_video.exercise = exercise
                exercise_video.video = db.Key(video_key)
                exercise_video.exercise_order = 0 #reordering below
                exercise_video.put() 

        # Start ordering
        exercise_videos = models.ExerciseVideo.all().filter('exercise =', exercise.key()).run()
        
        # get a dict of a topic : a dict of exercises_videos and the order of their videos in that topic
        topics = {}
        for exercise_video in exercise_videos:
            video_topics = db.get(exercise_video.video.topic_string_keys)
            for topic in video_topics:
                if not topics.has_key(topic.key()):
                    topics[topic.key()] = {}

                topics[topic.key()][exercise_video] = topic.get_child_order(exercise_video.video.key())

        # sort the list by topics that have the most exercises in them
        topic_list = sorted(topics.keys(), key = lambda k: len(topics[k]), reverse = True)  
        
        orders = {}
        i=0
        for topic_key in topic_list:
            # sort the exercise_videos in topic by their correct order
            exercise_video_list = sorted(topics[topic_key], key = lambda k: topics[topic_key][k])
            for exercise_video in exercise_video_list:
                # as long as the video hasn't already appeared in an earlier topic, it should appear next in the exercise's video list
                if not orders.has_key(exercise_video):
                    orders[exercise_video] = i
                    i += 1

        for exercise_video, i in orders.iteritems():
            exercise_video.exercise_order = i
        
        db.put(exercise_videos)

    def post(self):
        self.get()

    @user_util.developer_only
    def get(self):
        dict = {}
        dict["name"] = self.request.get('name')
        if not dict["name"]:
            self.response.out.write("No exercise submitted, please resubmit if you just logged in.")
            return

        dict["summative"] = self.request_bool('summative', default=False)
        dict["v_position"] = self.request.get('v_position')
        dict["h_position"] = self.request.get('h_position')
        dict["short_display_name"] = self.request.get('short_display_name')
        dict["live"] = self.request_bool("live", default=False)

        dict["prerequisites"] = []
        for c_check_prereq in range(0, 1000):
            prereq_append = self.request_string("prereq-%s" % c_check_prereq, default="")
            if prereq_append and not prereq_append in dict["prerequisites"]:
                dict["prerequisites"].append(prereq_append)

        dict["covers"] = []
        for c_check_cover in range(0, 1000):
            cover_append = self.request_string("cover-%s" % c_check_cover, default="")
            if cover_append and not cover_append in dict["covers"]:
                dict["covers"].append(cover_append)

        dict["related_video_keys"] = []
        dict["related_videos"] = []
        for c_check_video in range(0, 1000):
            video_name_append = self.request_string("video-%s-readable" % c_check_video, default="")
            if video_name_append and not video_name_append in dict["related_videos"]:
                dict["related_videos"].append(video_name_append)

            video_append = self.request_string("video-%s" % c_check_video, default="")
            if video_append and not video_append in dict["related_video_keys"]:
                dict["related_video_keys"].append(video_append)

        self.do_update(dict)

        self.redirect('/editexercise?saved=1&name=' + dict["name"])
