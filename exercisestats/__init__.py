import logging
import operator
import itertools
from time import mktime
import datetime
import math
import pickle
import hashlib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import deferred
from mapreduce import control
from mapreduce import operation as op

from app import App
import request_handler
import models
import consts
import user_util

from dashboard.models import DailyStatisticLog

class Test(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        problem_log_query = models.ProblemLog.all()
        problem_logs = problem_log_query.fetch(1000)

        problem_logs.sort(key=lambda log: log.time_taken)
        grouped = dict((k, sum(1 for i in v)) for (k, v) in itertools.groupby(problem_logs, key=lambda log: log.time_taken))

        hist = []
        total = sum(grouped[k] for k in grouped)
        cumulative = 0
        for time in range(180):
            count = grouped.get(time, 0)
            cumulative += count
            hist.append({
                'time': time,
                'count': count,
                'cumulative': cumulative,
                'percent': 100.0 * count / total,
                'percent_cumulative': 100.0 * cumulative / total,
                'percent_cumulative_tenth': 10.0 * cumulative / total,
            })

        context = { 'selected_nav_link': 'practice', 'hist': hist, 'total': total }

        self.render_template('exercisestats/test.html', context)

class KickOffDeferredStuff(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        exid = self.request_string('exid')
        days = self.request_float('days', default = 1.0)
        start_dt = datetime.datetime.now() - datetime.timedelta(days = days)
        deferred.defer(fancy_stats_deferred, exid, start_dt, None, _queue = 'fancy-exercise-stats-queue')
        self.response.out.write('started, methinks')

class ExerciseStatisticShard(db.Model):
    # key_name is fancy
    exid = db.StringProperty(required=True)
    start_dt = db.DateTimeProperty(required=True)
    cursor = db.StringProperty()
    blob_val = db.BlobProperty()

def fancy_stats_deferred(exid, start_dt, cursor):
    unix_time = int(mktime(start_dt.timetuple()))
    key_name = "%s:%d:%s" % (exid, unix_time, cursor)

    if cursor and ExerciseStatisticShard.get_by_key_name(key_name):
        # We've already run, die.
        return

    query = models.ProblemLog.all()
    query.filter('exercise =', exid)
    query.filter('correct = ', True)
    query.filter('time_done >', start_dt)
    query.order('-time_done')

    if cursor:
        query.with_cursor(cursor)

    # { time_taken: frequency } pairs
    freq_table = {}
    total_count = 0

    problem_logs = query.fetch(1000)
    if len(problem_logs) > 0:
        stats = fancy_stats_from_logs(problem_logs)
        pickled = pickle.dumps(stats)

        ExerciseStatisticShard.get_or_insert(
            key_name,
            exid = exid,
            start_dt = start_dt,
            cursor = cursor,
            blob_val = pickled)

        # task names must match ^[a-zA-Z0-9_-]{1,500}$
        task_name = hashlib.sha1(key_name).hexdigest()
        deferred.defer(fancy_stats_deferred, exid, start_dt, query.cursor(),
            _name = task_name,
            _queue = 'fancy-exercise-stats-queue')
    else:
        all_stats = fancy_stats_shard_reducer(exid, start_dt)
        logging.critical("%r", all_stats)

def fancy_stats_from_logs(problem_logs):
    logging.warn("processing %d logs" % len(problem_logs))

    freq_table = {}
    count = 0
    sugg_freq_table = {}
    prof_freq_table = {}

    for problem_log in problem_logs:
        # cast longs to ints when possible
        time = int(problem_log.time_taken)

        freq_table[time] = 1 + freq_table.get(time, 0)
        count += 1

        if problem_log.suggested:
            sugg_freq_table[time] = 1 + sugg_freq_table.get(time, 0)

        if problem_log.earned_proficiency:
            problem_num = int(problem_log.problem_number)
            prof_freq_table[problem_num] = 1 + prof_freq_table.get(problem_num, 0)

    return { 'time_taken_frequencies': freq_table, 'log_count': count, 'suggested_time_taken_frequencies': sugg_freq_table, 'proficiency_problem_number_frequencies': prof_freq_table }

def fancy_stats_shard_reducer(exid, start_dt):
    logging.warn("summing all stats")

    query = ExerciseStatisticShard.all()
    query.filter('exid =', exid)
    query.filter('start_dt =', start_dt)

    # log_count can't be just a normal variable because Python closures are confusing
    # http://stackoverflow.com/questions/4851463
    results = {
        'time_taken_frequencies': {},
        'log_count': 0,
        'suggested_time_taken_frequencies': {},
        'proficiency_problem_number_frequencies': {},
    }

    def accumulate_from_stat_shard(stat_shard):
        shard_val = pickle.loads(stat_shard.blob_val)
        freq_table = shard_val['time_taken_frequencies']
        sugg_freq_table = shard_val['suggested_time_taken_frequencies']
        prof_freq_table = shard_val['proficiency_problem_number_frequencies']

        for time in freq_table:
            so_far = results['time_taken_frequencies'].get(time, 0)
            results['time_taken_frequencies'][time] = freq_table[time] + so_far

        results['log_count'] += shard_val['log_count']

        for num in sugg_freq_table:
            so_far = results['suggested_time_taken_frequencies'].get(num, 0)
            results['suggested_time_taken_frequencies'][num] = sugg_freq_table[num] + so_far

        for num in prof_freq_table:
            so_far = results['proficiency_problem_number_frequencies'].get(num, 0)
            results['proficiency_problem_number_frequencies'][num] = prof_freq_table[num] + so_far

    while True:
        stat_shards = query.fetch(1000)

        if len(stat_shards) <= 0:
            break

        for stat_shard in stat_shards:
            accumulate_from_stat_shard(stat_shard)

        # Don't need the stat shards any more; get rid of them!
        db.delete(stat_shards)

        query.with_cursor(query.cursor())

    return results

# See http://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values/
def percentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (k-f)
    d1 = key(N[int(c)]) * (c-k)
    return d0+d1
