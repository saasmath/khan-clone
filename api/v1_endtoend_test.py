"""Tests of all the handlers in v1.py.

This includes end-to-end tests of all the handlers in v1.  (It's a
rather slow test because of that.)  Basically, it sends off a url
request and makes sure the response is sane.  end-to-end tests require a
running appengine instance: it will start an instance on an unused port.
"""

from testutil import handler_test_utils
from testutil import oauth_test_client
from testutil import testsize
try:
    import unittest2 as unittest     # python 2.5
except ImportError:
    import unittest                  # python 2.6+


@testsize.large()
def setUpModule():
    handler_test_utils.start_dev_appserver(db='testutil/test_db.sqlite')


def tearDownModule():
    handler_test_utils.stop_dev_appserver()


class V1EndToEndTestBase(unittest.TestCase):
    def setUp(self):
        """Reset to the default user, with no special privileges."""
        self.set_user()       # reset to the default values

    def set_user(self, moderator=False, developer=False, admin=False,
                 anointed_consumer=False):
        """Change the user for subsequent fetch calls to have these perms."""
        # The defaults, if not overridden below.
        self.email = 'user1@example.com'
        self.password = 'user1'

        if moderator:
            self.assertFalse(developer or admin, 'Can only have one right now')
            self.email = 'moderator@example.com'
            self.password = 'moderator'

        if developer:
            self.assertFalse(moderator or admin, 'Can only have one right now')
            self.email = 'developer@example.com'
            self.password = 'developer'

        if admin:
            self.assertFalse(moderator or developer,
                             'Can only have one right now')
            self.assertTrue(False, 'TODO(csilvers): make an admin user')

        self.consumer_is_anointed = anointed_consumer

    def fetch(self, path):
        """path is e.g. '/api/v1/users'. Does a lot, so makes a test large."""
        return oauth_test_client.fetch_via_oauth(
            handler_test_utils.appserver_url + path,
            email_of_user_wanting_access=self.email,
            password_of_user_wanting_access=self.password,
            consumer_is_anointed=self.consumer_is_anointed,
            method=self.method)

    def assertIn(self, needle, haystack):
        self.assertTrue(needle in haystack,
                        'Did not find "%s" in "%s"' % (needle, haystack))
    

class V1EndToEndGetTest(V1EndToEndTestBase):
    """Test all the GET methods in v1.py, except obsolete /playlist urls."""
    def setUp(self):
        super(V1EndToEndGetTest, self).setUp()
        self.method = "GET"

    @testsize.large()
    def test_topics__with_content(self):
        r = self.fetch('/api/v1/topics/with_content')
        # Topic-version 11 (the default) appends '[early]' to all titles.
        self.assertIn("[late]", r)
        self.assertIn("standalone_title", r)

    @testsize.large()
    def test_topicversion__version_id__topics__with_content(self):
        """2 is the non-default version in our test db."""
        r = self.fetch('/api/v1/topicversion/2/topics/with_content')
        # Topic-version 2 appends '[early]' to all titles.
        self.assertIn("[early]", r)

    @testsize.large()
    def test_topics__library__compact(self):
        r = self.fetch('/api/v1/topics/library/compact')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__changelist(self):
        # early version
        r = self.fetch('/api/v1/topicversion/2/changelist')
        self.assertIn("TODO(csilvers)", r)

        # later (default) version
        r = self.fetch('/api/v1/topicversion/11/changelist')
        self.assertIn("TODO(csilvers)", r)

        # non-existent version
        r = self.fetch('/api/v1/topicversion/1000/changelist')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__videos(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topic/<topic_id>/videos')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id__videos(self):
        r = self.fetch('/api/v1/topic/<topic_id>/videos')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__exercises(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topic/<topic_id>/exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id__exercises(self):
        r = self.fetch('/api/v1/topic/<topic_id>/exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id__progress(self):
        r = self.fetch('/api/v1/topic/<topic_id>/progress')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topictree(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topictree(self):
        r = self.fetch('/api/v1/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topictree__problems(self):
        r = self.fetch('/api/v1/dev/topictree/problems')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topicversion__version_id__topic__topic_id__topictree(self):
        r = self.fetch('/api/v1/dev/topicversion/<version_id>/topic/<topic_id>/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topicversion__version_id__topictree(self):
        r = self.fetch('/api/v1/dev/topicversion/<version_id>/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topictree(self):
        r = self.fetch('/api/v1/dev/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__search__query(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/search/<query>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topic/<topic_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id(self):
        r = self.fetch('/api/v1/topic/<topic_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__topic_page(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topic/<topic_id>/topic-page')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id__topic_page(self):
        r = self.fetch('/api/v1/topic/<topic_id>/topic-page')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__maplayout(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/maplayout')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_maplayout(self):
        r = self.fetch('/api/v1/maplayout')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__default__id(self):
        r = self.fetch('/api/v1/topicversion/default/id')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__task_message(self):
        r = self.fetch('/api/v1/dev/task_message')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__children(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topic/<topic_id>/children')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id__children(self):
        r = self.fetch('/api/v1/topic/<topic_id>/children')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__setdefault(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/setdefault')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversions__(self):
        r = self.fetch('/api/v1/topicversions/')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__unused_content(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/unused_content')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__url__url_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/url/<url_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_url__url_id(self):
        r = self.fetch('/api/v1/url/<url_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__video_id__explore_url(self):
        r = self.fetch('/api/v1/videos/<video_id>/explore_url')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_exercises(self):
        r = self.fetch('/api/v1/exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__exercises__exercise_name(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/exercises/<exercise_name>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_exercises__exercise_name(self):
        r = self.fetch('/api/v1/exercises/<exercise_name>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_exercises__recent(self):
        r = self.fetch('/api/v1/exercises/recent')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_exercises__exercise_name__followup_exercises(self):
        r = self.fetch('/api/v1/exercises/<exercise_name>/followup_exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_exercises__exercise_name__videos(self):
        r = self.fetch('/api/v1/exercises/<exercise_name>/videos')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__videos__video_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/videos/<video_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__video_id(self):
        r = self.fetch('/api/v1/videos/<video_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__recent(self):
        r = self.fetch('/api/v1/videos/recent')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__video_id__exercises(self):
        r = self.fetch('/api/v1/videos/<video_id>/exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__topic_id__video_id__play(self):
        r = self.fetch('/api/v1/videos/<topic_id>/<video_id>/play')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_commoncore(self):
        r = self.fetch('/api/v1/commoncore')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__youtube_id__youtubeinfo(self):
        r = self.fetch('/api/v1/videos/<youtube_id>/youtubeinfo')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user(self):
        """Test that the result is json and has the appropriate fields."""
        r = self.fetch('/api/v1/user')    
        self.assertIn("user_id", r)

    @testsize.large()
    def test_user__username_available(self):
        r = self.fetch('/api/v1/user/username_available')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__promo__promo_name(self):
        r = self.fetch('/api/v1/user/promo/<promo_name>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__profile(self):
        r = self.fetch('/api/v1/user/profile')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__coaches(self):
        r = self.fetch('/api/v1/user/coaches')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__students(self):
        r = self.fetch('/api/v1/user/students')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__studentlists(self):
        r = self.fetch('/api/v1/user/studentlists')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__videos(self):
        r = self.fetch('/api/v1/user/videos')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__videos__youtube_id(self):
        r = self.fetch('/api/v1/user/videos/<youtube_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__videos__youtube_id__log_compatability(self):
        r = self.fetch('/api/v1/user/videos/<youtube_id>/log_compatability')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__topic__topic_id__exercises__next(self):
        r = self.fetch('/api/v1/user/topic/<topic_id>/exercises/next')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises(self):
        r = self.fetch('/api/v1/user/exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__topic__topic_id__exercises(self):
        r = self.fetch('/api/v1/user/topic/<topic_id>/exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__students__progress__summary(self):
        r = self.fetch('/api/v1/user/students/progress/summary')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name(self):
        r = self.fetch('/api/v1/user/exercises/<exercise_name>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name__followup_exercises(self):
        r = self.fetch('/api/v1/user/exercises/<exercise_name>/followup_exercises')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__topics(self):
        r = self.fetch('/api/v1/user/topics')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__topic__topic_id(self):
        r = self.fetch('/api/v1/user/topic/<topic_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__reviews__count(self):
        r = self.fetch('/api/v1/user/exercises/reviews/count')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name__log(self):
        r = self.fetch('/api/v1/user/exercises/<exercise_name>/log')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__videos__youtube_id__log(self):
        r = self.fetch('/api/v1/user/videos/<youtube_id>/log')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_badges(self):
        r = self.fetch('/api/v1/badges')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_badges__categories(self):
        r = self.fetch('/api/v1/badges/categories')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_badges__categories__category(self):
        r = self.fetch('/api/v1/badges/categories/<category>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__badges(self):
        r = self.fetch('/api/v1/user/badges')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__activity(self):
        r = self.fetch('/api/v1/user/activity')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_autocomplete(self):
        r = self.fetch('/api/v1/autocomplete')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__backupmodels(self):
        r = self.fetch('/api/v1/dev/backupmodels')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__protobufquery(self):
        r = self.fetch('/api/v1/dev/protobufquery')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__protobuf__entity(self):
        r = self.fetch('/api/v1/dev/protobuf/<entity>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__problems(self):
        r = self.fetch('/api/v1/dev/problems')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__videos(self):
        r = self.fetch('/api/v1/dev/videos')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__users(self):
        r = self.fetch('/api/v1/dev/users')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__students__progressreport(self):
        r = self.fetch('/api/v1/user/students/progressreport')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals(self):
        r = self.fetch('/api/v1/user/goals')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals__current(self):
        r = self.fetch('/api/v1/user/goals/current')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__students__goals(self):
        r = self.fetch('/api/v1/user/students/goals')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals__id(self):
        r = self.fetch('/api/v1/user/goals/<id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_avatars(self):
        r = self.fetch('/api/v1/avatars')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__version(self):
        r = self.fetch('/api/v1/dev/version')
        self.assertIn("TODO(csilvers)", r)


class V1EndToEndDeleteTest(V1EndToEndTestBase):
    """Test all the DELETE methods in v1.py."""
    def setUp(self):
        # TODO(csilvers): reset the database before each of these.
        super(V1EndToEndDeleteTest, self).setUp()
        self.method = "DELETE"

    @testsize.large()
    def test_user__studentlists__list_key(self):
        r = self.fetch('/api/v1/user/studentlists/list_key>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals__id(self):
        r = self.fetch('/api/v1/user/goals/id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals(self):
        r = self.fetch('/api/v1/user/goals')
        self.assertIn("TODO(csilvers)", r)


class V1EndToEndPostTest(V1EndToEndTestBase):
    """Test all the POST methods in v1.py."""
    def setUp(self):
        # TODO(csilvers): reset the database before each of these.
        super(V1EndToEndPostTest, self).setUp()
        self.method = "POST"

    # Note some of these also accept PUT, but we don't seem to distinguish.

    @testsize.large()
    def test_topicversion__version_id__exercises__exercise_name(self):
        r = self.fetch('/api/v1/topicversion/version_id/exercises/exercise_name>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__videos__(self):
        r = self.fetch('/api/v1/topicversion/version_id/videos/')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__videos__video_id(self):
        r = self.fetch('/api/v1/topicversion/version_id/videos/video_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__profile(self):
        r = self.fetch('/api/v1/user/profile')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__badges__public(self):
        r = self.fetch('/api/v1/user/badges/public')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_parentsignup(self):
        r = self.fetch('/api/v1/parentsignup')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__(self):
        r = self.fetch('/api/v1/videos/')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__video_id(self):
        r = self.fetch('/api/v1/videos/video_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__deletechange(self):
        r = self.fetch('/api/v1/topicversion/version_id/deletechange')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__parent_id__addchild(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/parent_id/addchild')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__parent_id__addchild(self):
        r = self.fetch('/api/v1/topic/parent_id/addchild')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__parent_id__deletechild(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/parent_id/deletechild')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__parent_id__deletechild(self):
        r = self.fetch('/api/v1/topic/parent_id/deletechild')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__old_parent_id__movechild(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/old_parent_id/movechild')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__old_parent_id__movechild(self):
        r = self.fetch('/api/v1/topic/old_parent_id/movechild')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__ungroup(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/topic_id/ungroup')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id__ungroup(self):
        r = self.fetch('/api/v1/topic/topic_id/ungroup')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__video_id__download_available(self):
        r = self.fetch('/api/v1/videos/video_id/download_available')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__promo__promo_name(self):
        r = self.fetch('/api/v1/user/promo/promo_name>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__studentlists(self):
        r = self.fetch('/api/v1/user/studentlists')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__videos__youtube_id__log(self):
        r = self.fetch('/api/v1/user/videos/youtube_id/log')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name__problems__problem_number__attempt(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/problems/problem_number/attempt')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name__problems__problem_number__hint(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/problems/problem_number/hint')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name__reset_streak(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/reset_streak')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__exercises__exercise_name__wrong_attempt(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/wrong_attempt')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_developers__add(self):
        r = self.fetch('/api/v1/developers/add')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_developers__remove(self):
        r = self.fetch('/api/v1/developers/remove')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_coworkers__add(self):
        r = self.fetch('/api/v1/coworkers/add')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_coworkers__remove(self):
        r = self.fetch('/api/v1/coworkers/remove')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals(self):
        r = self.fetch('/api/v1/user/goals')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_exercises__exercise_name(self):
        r = self.fetch('/api/v1/exercises/exercise_name>')
        self.assertIn("TODO(csilvers)", r)


class V1EndToEndPutTest(V1EndToEndTestBase):
    """Test all the PUT methods in v1.py."""
    def setUp(self):
        # TODO(csilvers): reset the database before each of these.
        super(V1EndToEndPutTest, self).setUp()
        self.method = "PUT"

    @testsize.large()
    def test_dev__topicversion__version_id__topic__topic_id__topictree(self):
        r = self.fetch('/api/v1/dev/topicversion/version_id/topic/topic_id/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topicversion__version_id__topictree(self):
        r = self.fetch('/api/v1/dev/topicversion/version_id/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topictree__init__publish(self):
        r = self.fetch('/api/v1/dev/topictree/init/publish>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_dev__topictree(self):
        r = self.fetch('/api/v1/dev/topictree')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/topic_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topic__topic_id(self):
        r = self.fetch('/api/v1/topic/topic_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__maplayout(self):
        r = self.fetch('/api/v1/topicversion/version_id/maplayout')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_maplayout(self):
        r = self.fetch('/api/v1/maplayout')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id(self):
        r = self.fetch('/api/v1/topicversion/version_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__url__(self):
        r = self.fetch('/api/v1/topicversion/version_id/url/')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_topicversion__version_id__url__url_id(self):
        r = self.fetch('/api/v1/topicversion/version_id/url/url_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_url__(self):
        r = self.fetch('/api/v1/url/')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_url__url_id(self):
        r = self.fetch('/api/v1/url/url_id>')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_videos__video_id__explore_url(self):
        r = self.fetch('/api/v1/videos/video_id/explore_url')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__coaches(self):
        r = self.fetch('/api/v1/user/coaches')
        self.assertIn("TODO(csilvers)", r)

    @testsize.large()
    def test_user__goals__id(self):
        r = self.fetch('/api/v1/user/goals/id>')
        self.assertIn("TODO(csilvers)", r)

