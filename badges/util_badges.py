import logging
import datetime
import sys

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from google.appengine.api import taskqueue
from mapreduce import control

import models
import badges
import models_badges
import last_action_cache

import custom_badges
import topic_exercise_badges
import streak_badges
import timed_problem_badges
import exercise_completion_badges
import exercise_completion_count_badges
import topic_time_badges
import power_time_badges
import profile_badges
import recovery_problem_badges
import unfinished_exercise_badges
import points_badges
import tenure_badges
import video_time_badges
import consecutive_activity_badges
import discussion_badges
import feedback_badges

import layer_cache
import request_handler
import user_util

# Authoritative list of all badges
@layer_cache.cache_with_key_fxn(lambda: "all_badges:%s" % models.Setting.topic_tree_version())
def all_badges():
    list_badges = [
        exercise_completion_count_badges.GettingStartedBadge(),
        exercise_completion_count_badges.MakingProgressBadge(),
        exercise_completion_count_badges.HardAtWorkBadge(),
        exercise_completion_count_badges.WorkHorseBadge(),
        exercise_completion_count_badges.MagellanBadge(),
        exercise_completion_count_badges.CopernicusBadge(),
        exercise_completion_count_badges.KeplerBadge(),
        exercise_completion_count_badges.AtlasBadge(),

        points_badges.TenThousandaireBadge(),
        points_badges.HundredThousandaireBadge(),
        points_badges.FiveHundredThousandaireBadge(),
        points_badges.MillionaireBadge(),
        points_badges.TenMillionaireBadge(),

        streak_badges.NiceStreakBadge(),
        streak_badges.GreatStreakBadge(),
        streak_badges.AwesomeStreakBadge(),
        streak_badges.RidiculousStreakBadge(),
        streak_badges.LudicrousStreakBadge(),

        topic_time_badges.NiceTopicTimeBadge(),
        topic_time_badges.GreatTopicTimeBadge(),
        topic_time_badges.AwesomeTopicTimeBadge(),
        topic_time_badges.RidiculousTopicTimeBadge(),
        topic_time_badges.LudicrousTopicTimeBadge(),

        timed_problem_badges.NiceTimedProblemBadge(),
        timed_problem_badges.GreatTimedProblemBadge(),
        timed_problem_badges.AwesomeTimedProblemBadge(),
        timed_problem_badges.RidiculousTimedProblemBadge(),
        timed_problem_badges.LudicrousTimedProblemBadge(),

        recovery_problem_badges.RecoveryBadge(),
        recovery_problem_badges.ResurrectionBadge(),

        unfinished_exercise_badges.SoCloseBadge(),
        unfinished_exercise_badges.KeepFightingBadge(),
        unfinished_exercise_badges.UndeterrableBadge(),

        power_time_badges.PowerFifteenMinutesBadge(),
        power_time_badges.PowerHourBadge(),
        power_time_badges.DoublePowerHourBadge(),

        profile_badges.ProfileCustomizationBadge(),

        exercise_completion_badges.LevelOneArithmeticianBadge(),
        exercise_completion_badges.LevelTwoArithmeticianBadge(),
        exercise_completion_badges.LevelThreeArithmeticianBadge(),
        exercise_completion_badges.TopLevelArithmeticianBadge(),

        exercise_completion_badges.LevelOneTrigonometricianBadge(),
        exercise_completion_badges.LevelTwoTrigonometricianBadge(),
        exercise_completion_badges.LevelThreeTrigonometricianBadge(),
        exercise_completion_badges.TopLevelTrigonometricianBadge(),

        exercise_completion_badges.LevelOnePrealgebraistBadge(),
        exercise_completion_badges.LevelTwoPrealgebraistBadge(),
        exercise_completion_badges.LevelThreePrealgebraistBadge(),
        exercise_completion_badges.TopLevelPrealgebraistBadge(),

        exercise_completion_badges.LevelOneAlgebraistBadge(),
        exercise_completion_badges.LevelTwoAlgebraistBadge(),
        exercise_completion_badges.LevelThreeAlgebraistBadge(),
        exercise_completion_badges.LevelFourAlgebraistBadge(),
        exercise_completion_badges.LevelFiveAlgebraistBadge(),
        exercise_completion_badges.TopLevelAlgebraistBadge(),

        tenure_badges.YearOneBadge(),
        tenure_badges.YearTwoBadge(),
        tenure_badges.YearThreeBadge(),

        video_time_badges.ActOneSceneOneBadge(),

        consecutive_activity_badges.FiveDayConsecutiveActivityBadge(),
        consecutive_activity_badges.FifteenDayConsecutiveActivityBadge(),
        consecutive_activity_badges.ThirtyDayConsecutiveActivityBadge(),
        consecutive_activity_badges.HundredDayConsecutiveActivityBadge(),

        feedback_badges.LevelOneAnswerVoteCountBadge(),
        feedback_badges.LevelTwoAnswerVoteCountBadge(),
        feedback_badges.LevelThreeAnswerVoteCountBadge(),

        feedback_badges.LevelOneQuestionVoteCountBadge(),
        feedback_badges.LevelTwoQuestionVoteCountBadge(),
        feedback_badges.LevelThreeQuestionVoteCountBadge(),

        discussion_badges.FirstFlagBadge(),
        discussion_badges.FirstUpVoteBadge(),
        discussion_badges.FirstDownVoteBadge(),
        discussion_badges.ModeratorBadge(),

    ]

    # Add custom badges and topic exercise badges, which both correspond
    # to datastore entities, to the collection of all badges.
    list_badges.extend(custom_badges.CustomBadge.all())
    list_badges.extend(topic_exercise_badges.TopicExerciseBadge.all())

    return list_badges

@layer_cache.cache_with_key_fxn(lambda: "all_badges_dict:%s" % models.Setting.topic_tree_version())
def all_badges_dict():
    dict_badges = {}
    for badge in all_badges():
        dict_badges[badge.name] = badge
    return dict_badges

def badges_with_context_type(badge_context_type):
    return filter(lambda badge: badge.badge_context_type == badge_context_type, all_badges())

def get_badge_counts(user_data):

    count_dict = badges.BadgeCategory.empty_count_dict()

    if not user_data:
        return count_dict

    badges_dict = all_badges_dict()

    for badge_name_with_context in user_data.badges:
        badge_name = badges.Badge.remove_target_context(badge_name_with_context)
        badge = badges_dict.get(badge_name)
        if badge:
            count_dict[badge.badge_category] += 1

    return count_dict

def get_grouped_user_badges(user_data=None):
    """ Retrieves the list of user-earned badges grouped into GroupedUserBadge
    objects. Also returns the list of possible badges along with them.

    """

    if not user_data:
        user_data = models.UserData.current()

    user_badges = []
    grouped_badges_dict = {}

    if user_data:
        user_badges = models_badges.UserBadge.get_for(user_data)
        badges_dict = all_badges_dict()
        grouped_user_badge = None
        for user_badge in user_badges:
            if (grouped_user_badge and
                    grouped_user_badge.badge.name == user_badge.badge_name):
                grouped_user_badge.target_context_names.append(
                    user_badge.target_context_name)
            else:
                badge = badges_dict.get(user_badge.badge_name)
                if badge is None:
                    logging.warning("Can't find reference badge named %s" %
                                    user_badge.badge_name)
                    continue
                badge.is_owned = True
                grouped_user_badge = badges.GroupedUserBadge.build(user_data,
                                                                   badge,
                                                                   user_badge)
                grouped_badges_dict[user_badge.badge_name] = grouped_user_badge

    possible_badges = sorted(all_badges(),
                             key=lambda badge:badge.badge_category)
    for badge in possible_badges:
        badge.is_owned = grouped_badges_dict.has_key(badge.name)
        badge.can_become_goal = user_data and not user_data.is_phantom and not badge.is_owned and badge.is_goal
        if badge.can_become_goal:
            # TODO is there a way to have handlebars json.stringify() a variable?
            badge.objectives = json.dumps(badge.exercise_names_required)

    possible_badges = filter(lambda badge: not badge.is_hidden(), possible_badges)

    grouped_user_badges = sorted(
            filter(lambda group: (hasattr(group, "badge") and
                                  group.badge is not None),
                   grouped_badges_dict.values()),
            reverse=True,
            key=lambda group: group.last_earned_date)

    def filter_by_category(category):
        return filter(lambda group: group.badge.badge_category == category,
                      grouped_user_badges)

    user_badges_normal = filter(lambda group: group.badge.badge_category != badges.BadgeCategory.MASTER,
                                grouped_user_badges)
    user_badges_master = filter_by_category(badges.BadgeCategory.MASTER)
    user_badges_diamond = filter_by_category(badges.BadgeCategory.DIAMOND)
    user_badges_platinum = filter_by_category(badges.BadgeCategory.PLATINUM)
    user_badges_gold = filter_by_category(badges.BadgeCategory.GOLD)
    user_badges_silver = filter_by_category(badges.BadgeCategory.SILVER)
    user_badges_bronze = filter_by_category(badges.BadgeCategory.BRONZE)

    def filter_and_sort(category):
        return sorted(filter(lambda badge: badge.badge_category == category,
                             possible_badges),
                      key=lambda badge: badge.points or sys.maxint)

    bronze_badges = filter_and_sort(badges.BadgeCategory.BRONZE)
    silver_badges = filter_and_sort(badges.BadgeCategory.SILVER)
    gold_badges = filter_and_sort(badges.BadgeCategory.GOLD)
    platinum_badges = filter_and_sort(badges.BadgeCategory.PLATINUM)
    diamond_badges = filter_and_sort(badges.BadgeCategory.DIAMOND)
    master_badges = filter_and_sort(badges.BadgeCategory.MASTER)

    return { 'possible_badges': possible_badges,
             'user_badges_normal': user_badges_normal,
             'user_badges_master': user_badges_master,
             "badge_collections": [bronze_badges, silver_badges, gold_badges, platinum_badges, diamond_badges, master_badges],
             'bronze_badges': user_badges_bronze,
             'silver_badges': user_badges_silver,
             'gold_badges': user_badges_gold,
             'platinum_badges': user_badges_platinum,
             'diamond_badges': user_badges_diamond, }

EMPTY_BADGE_NAME = "__empty__"
NUM_PUBLIC_BADGE_SLOTS = 5

def get_public_user_badges(user_data=None):
    """ Retrieves the list of user-earned badges that the user has selected
    to publicly display on his/her profile display-case.
    This is returned as a list of Badge objects, and not UserBadge objects
    and therefore does not contain further information about the user's
    activities.

    """
    if not user_data:
        user_data = models.UserData.current()
        if not user_data:
            return []

    public_badges = user_data.public_badges or []
    full_dict = all_badges_dict()
    results = []
    for name in public_badges:
        if name in full_dict:
            results.append(full_dict[name])
        else:
            # assert - name is "__empty__"
            results.append(None) # empty slot
    return results

class ViewBadges(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):
        user_data = models.UserData.current() or models.UserData.pre_phantom()
        grouped_badges = get_grouped_user_badges(user_data)
        self.render_jinja2_template('viewbadges.html', grouped_badges)

# /admin/badgestatistics is called periodically by a cron job
class BadgeStatistics(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):
        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.
        taskqueue.add(url='/admin/badgestatistics', queue_name='badge-statistics-queue', params={'start': '1'})
        self.response.out.write("Badge statistics task started.")

    @user_util.open_access
    def post(self):
        if not self.request_bool("start", default=False):
            return

        for badge in all_badges():

            badge_stat = models_badges.BadgeStat.get_or_insert_for(badge.name)

            if badge_stat and badge_stat.needs_update():
                badge_stat.update()
                badge_stat.put()

# /admin/startnewbadgemapreduce is called periodically by a cron job
class StartNewBadgeMapReduce(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):

        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.

        # Start a new Mapper task for calling badge_update_map
        mapreduce_id = control.start_map(
                name = "UpdateUserBadges",
                handler_spec = "badges.util_badges.badge_update_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "models.UserData"},
                mapreduce_parameters = {"processing_rate": 250},
                shard_count = 64,
                queue_name = "user-badge-queue"
                )

        self.response.out.write("OK: " + str(mapreduce_id))

def is_badge_review_waiting(user_data):
    if not user_data:
        return False

    if not user_data.user:
        return False

    if not user_data.user_id:
        logging.error("UserData with user and no current_user: %s" % user_data.email)
        return False

    if user_data.is_phantom:
        # Don't bother doing overnight badge reviews for phantom users -- we're not that worried about it,
        # and it reduces task queue stress.
        return False

    if not user_data.last_activity or (user_data.last_badge_review and user_data.last_activity <= user_data.last_badge_review):
        # No activity since last badge review, skip
        return False

    return True

def badge_update_map(user_data):

    if not is_badge_review_waiting(user_data):
        return

    action_cache = last_action_cache.LastActionCache.get_for_user_data(user_data)

    # Update all no-context badges
    update_with_no_context(user_data, action_cache=action_cache)

    # Update all exercise-context badges
    for user_exercise in models.UserExercise.get_for_user_data(user_data):
        update_with_user_exercise(user_data, user_exercise, action_cache=action_cache)

    # Update all topic-context badges
    for user_topic in models.UserTopic.get_for_user_data(user_data):
        update_with_user_topic(user_data, user_topic, action_cache=action_cache)

    user_data.last_badge_review = datetime.datetime.now()
    user_data.put()

# Award this user any earned no-context badges.
def update_with_no_context(user_data, action_cache = None):
    possible_badges = badges_with_context_type(badges.BadgeContextType.NONE)
    action_cache = action_cache or last_action_cache.LastActionCache.get_for_user_data(user_data)

    awarded = False
    for badge in possible_badges:
        if badge.is_manually_awarded():
            continue
        if not badge.is_already_owned_by(user_data=user_data):
            if badge.is_satisfied_by(user_data=user_data, action_cache=action_cache):
                badge.award_to(user_data=user_data)
                awarded = True

    return awarded

# Award this user any earned Exercise-context badges for the provided UserExercise.
def update_with_user_exercise(user_data, user_exercise, include_other_badges = False, action_cache = None):
    possible_badges = badges_with_context_type(badges.BadgeContextType.EXERCISE)
    action_cache = action_cache or last_action_cache.LastActionCache.get_for_user_data(user_data)

    awarded = False
    for badge in possible_badges:
        if badge.is_manually_awarded():
            continue
        # Pass in pre-retrieved user_exercise data so each badge check doesn't have to talk to the datastore
        if not badge.is_already_owned_by(user_data=user_data, user_exercise=user_exercise):
            if badge.is_satisfied_by(user_data=user_data, user_exercise=user_exercise, action_cache=action_cache):
                badge.award_to(user_data=user_data, user_exercise=user_exercise)
                awarded = True

    if include_other_badges:
        awarded = update_with_no_context(user_data, action_cache=action_cache) or awarded

    return awarded

# Award this user any earned Topic-context badges for the provided UserTopic.
def update_with_user_topic(user_data, user_topic, include_other_badges = False, action_cache = None):
    possible_badges = badges_with_context_type(badges.BadgeContextType.TOPIC)
    action_cache = action_cache or last_action_cache.LastActionCache.get_for_user_data(user_data)

    awarded = False
    for badge in possible_badges:
        if badge.is_manually_awarded():
            continue
        # Pass in pre-retrieved user_topic data so each badge check doesn't have to talk to the datastore
        if not badge.is_already_owned_by(user_data=user_data, user_topic=user_topic):
            if badge.is_satisfied_by(user_data=user_data, user_topic=user_topic, action_cache=action_cache):
                badge.award_to(user_data=user_data, user_topic=user_topic)
                awarded = True

    if include_other_badges:
        awarded = update_with_no_context(user_data, action_cache=action_cache) or awarded

    return awarded

