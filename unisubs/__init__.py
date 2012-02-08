import uuid
import urllib
import logging

from google.appengine.api import urlfetch
from google.appengine.ext import deferred

from models import Video
from models import VideoSubtitles
from models import VideoSubtitlesFetchReport
import request_handler

BATCH_SIZE = 5
DEFER_SECONDS = 1
TIMEOUT_SECONDS = 5
REPORT_TEMPLATE = (('status', 'started'), ('fetches', 0), ('writes', 0),
                   ('errors', 0), ('redirects', 0))
YOUTUBE_URL = 'http://www.youtube.com/watch?v=%s'
UNISUBS_URL = 'http://www.universalsubtitles.org/api/1.0/subtitles/?language=en&video_url=%s'


class ReportHandler(request_handler.RequestHandler):
    def get(self):
        """Display reports from recent imports"""
        limit = self.request_int('limit', 25)
        started = self.request_string('_started')

        query = VideoSubtitlesFetchReport().all()
        query.order('-created')
        reports = query.fetch(limit + 1)

        truncated = False
        if len(reports) > limit:
            truncated = True
            reports.pop()

        self.render_jinja2_template('unisubs_report.html', {'reports': reports,
                'truncated': truncated, 'started': started})


class ImportHandler(request_handler.RequestHandler):
    def get(self):
        """Start the subtitles import task chain

        This entry point is intended to be run as a cron.yaml scheduled task.
        """
        self.post()

    def post(self):
        """Start the subtitles import task chain

        This entry point is intended to be run as a manual HTTP POST.
        """
        uid = str(uuid.uuid4())
        deferred.defer(_task_handler, uid, _name=uid)

        interactive = self.request_bool('interactive', False)
        if interactive:
            self.redirect('/admin/unisubs?_started=%s' % uid)
        else:
            self.response.write('task chain started with id: %s' % uid)


def _task_report_handler(uid, report):
    """Report the results of a task chain

    Once scheduled, this task will retry until it succeeds.
    """
    report['status'] = 'finished'
    VideoSubtitlesFetchReport(key_name=uid, **report).put()


def _task_handler(uid, task_id=0, cursor=None, report=None):
    """Task chain for fetching subtitles from the Universal Subtitles API

    It processes Video models in batches of BATCH_SIZE by fetching the English
    subtitles via an HTTP API call.

    This job runs regularly so fetch failures are fixed from run-to-run.  Fetch
    failures are logged and suppressed as the task marches on.

    Errors include URL fetch timeouts, subtitles put failures, and response
    decoding failures.

    HTTP redirects indicate that the code needs updating to a new API endpoint.
    They are detected and reported separately.
    """

    query = Video.all()
    query.with_cursor(cursor)
    videos = query.fetch(BATCH_SIZE)

    if report is None:
        report = dict(REPORT_TEMPLATE)
        VideoSubtitlesFetchReport(key_name=uid, **report).put()

    # Asynchronously fetch. We'll rate-limit by fetching BATCH_SIZE subtitles
    # at each DEFER_SECONDS interval

    rpcs = []
    for video in videos:
        url = UNISUBS_URL % urllib.quote(YOUTUBE_URL % video.youtube_id)
        rpc = urlfetch.create_rpc(deadline=TIMEOUT_SECONDS)
        urlfetch.make_fetch_call(rpc, url)
        rpcs.append((video.youtube_id, rpc))
        report['fetches'] += 1

    # Process asynchronous fetches

    for youtube_id, rpc in rpcs:
        try:
            resp = rpc.get_result()
            if resp.status_code != 200:
                raise RuntimeError()

            if resp.final_url:
                logging.warn('youtube_id=%s: redirect to %s' % (youtube_id,
                                                                resp.final_url))
                report['redirects'] += 1

            json = resp.content.decode('utf-8')

            # Only update stale records

            key_name = 'en_%s' % youtube_id
            current = VideoSubtitles.get_by_key_name(key_name)
            if not current or current.json != json:
                new = VideoSubtitles(key_name=key_name, youtube_id=youtube_id,
                                     language='en', json=json)
                new.put()
                report['writes'] += 1
            else:
                logging.info('youtube_id=%s: content already up-to-date' %
                             youtube_id)
        except:
            logging.error('youtube_id=%s: subtitles fetch failed' % youtube_id)
            report['errors'] += 1

    # Generate a report if there is nothing left to process

    if len(videos) < BATCH_SIZE:
        deferred.defer(_task_report_handler, uid, report, _name='%s_report' % uid)
    else:
        next_id = task_id + 1
        cursor = query.cursor()
        deferred.defer(_task_handler, uid, next_id, cursor, report,
                       _name='%s_%s' % (uid, next_id),
                       _countdown=DEFER_SECONDS)
