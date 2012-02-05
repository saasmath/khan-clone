import datetime

import util
import models
import templatefilters
from badges import util_badges, models_badges
from templatefilters import seconds_to_time_string
from goals.models import GoalList

# Number of hours until activity is no longer considered "recent" for profiles
HOURS_RECENT_ACTIVITY = 4320 # OK for now, fix before shipping!
# Number of most-recent items shown in recent activity
MOST_RECENT_ITEMS = 10

class RecentActivity(object):
    def can_combine_dates(self, dt_a, dt_b):
        return (max(dt_b, dt_a) - min(dt_b, dt_a)) < datetime.timedelta(minutes=30)

    def combine_with(self, recent_activity):
        return False

class RecentBadgeActivity(RecentActivity):
    def __init__(self, user_badge, badge):
        self.s_type = "Badge"
        self.user_badge = user_badge
        self.badge = badge
        self.dt = user_badge.date

class RecentExerciseActivity(RecentActivity):
    def __init__(self, problem_log):
        self.s_type = "Exercise"
        self.exercise = problem_log.exercise
        self.dt = problem_log.time_done
        self.c_problems = 1
        self.earned_proficiency = problem_log.earned_proficiency
        self.exercise_display_name = models.Exercise.to_display_name(problem_log.exercise)

    def combine_with(self, recent_activity):
        if self.__class__ == recent_activity.__class__:
            if self.exercise == recent_activity.exercise:
                if self.can_combine_dates(self.dt, recent_activity.dt):
                    self.dt = recent_activity.dt
                    self.c_problems += 1
                    self.earned_proficiency = self.earned_proficiency or recent_activity.earned_proficiency
                    return True
        return False

class RecentVideoActivity(RecentActivity):
    def __init__(self, video_log):
        self.s_type = "Video"
        self.youtube_id = video_log.video.youtube_id
        self.video_title = video_log.video_title
        self.seconds_watched = video_log.seconds_watched
        self.dt = video_log.time_watched

    def combine_with(self, recent_activity):
        if self.__class__ == recent_activity.__class__:
            if self.video_title == recent_activity.video_title:
                if self.can_combine_dates(self.dt, recent_activity.dt):
                    self.dt = recent_activity.dt
                    self.seconds_watched += recent_activity.seconds_watched
                    return True
        return False

class RecentGoalActivity(RecentActivity):
    def __init__(self, goal):
        self.s_type = "Goal"
        self.goal = goal
        self.dt = goal.completed_on

def recent_badge_activity(user_badges):
    badges_dict = util_badges.all_badges_dict()
    list_badge_activity = []

    for user_badge in user_badges:
        badge = badges_dict.get(user_badge.badge_name)
        if badge:
            list_badge_activity.append(RecentBadgeActivity(user_badge, badge))

    return list_badge_activity

def recent_exercise_activity(problem_logs):
    return [RecentExerciseActivity(p) for p in problem_logs]

def recent_video_activity(video_logs):
    return [RecentVideoActivity(v) for v in video_logs]

def recent_goal_activity(goals):
    return [RecentGoalActivity(g) for g in goals
        if g.completed and not g.abandoned]

def recent_activity_for(user_data, dt_start, dt_end):

    query_user_badges = models_badges.UserBadge.get_for_user_data_between_dts(user_data, dt_start, dt_end)
    query_problem_logs = models.ProblemLog.get_for_user_data_between_dts(user_data, dt_start, dt_end)
    query_video_logs = models.VideoLog.get_for_user_data_between_dts(user_data, dt_start, dt_end)
    query_goals = GoalList.get_updated_between_dts(user_data, dt_start, dt_end)

    results = util.async_queries([query_user_badges, query_problem_logs,
        query_video_logs, query_goals], limit=200)

    list_recent_activity_types = [
            recent_badge_activity(results[0].get_result()),
            recent_exercise_activity(results[1].get_result()),
            recent_video_activity(results[2].get_result()),
            recent_goal_activity(results[3].get_result()),
    ]
    list_recent_activity = [activity for sublist in list_recent_activity_types for activity in sublist]

    return collapse_recent_activity(list_recent_activity)[:MOST_RECENT_ITEMS]

def collapse_recent_activity(list_recent_activity):

    last_recent_activity = None

    for ix in range(len(list_recent_activity)):
        recent_activity = list_recent_activity[ix]
        if last_recent_activity and last_recent_activity.combine_with(recent_activity):
            list_recent_activity[ix] = None
        else:
            last_recent_activity = recent_activity

    return sorted(filter(lambda activity: activity is not None, list_recent_activity), reverse=True, key=lambda activity: activity.dt)

def recent_activity_context(user_data):
    list_recent_activity = []
    if user_data:
        dt_end = datetime.datetime.now()
        dt_start = dt_end - datetime.timedelta(hours=HOURS_RECENT_ACTIVITY)
        list_recent_activity = recent_activity_for(user_data, dt_start, dt_end)
    return {
        "user_data_student": user_data,
        "list_recent_activity": list_recent_activity
    }
