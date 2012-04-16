"""Tests of all the handlers in v1.py.

This includes end-to-end tests of all the handlers in v1.  (It's a
rather slow test because of that.)  Basically, it sends off a url
request and makes sure the response is sane.  end-to-end tests require a
running appengine instance: it will start an instance on an unused port.
"""

import urllib2

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

    def assertNotIn(self, needle, haystack):
        self.assertFalse(needle in haystack,
                        'Unexpectedly found "%s" in "%s"' % (needle, haystack))
    

class V1EndToEndGetTest(V1EndToEndTestBase):
    """Test all the GET methods in v1.py, except obsolete /playlist urls."""
    def setUp(self):
        super(V1EndToEndGetTest, self).setUp()
        self.method = 'GET'

    @testsize.large()
    def test_topics__with_content(self):
        r = self.fetch('/api/v1/topics/with_content')
        # Topic-version 11 (the default) appends '[late]' to all titles.
        self.assertIn('"standalone_title": "Mathematics [late]"', r)

    @testsize.large()
    def test_topicversion__version_id__topics__with_content(self):
        '''2 is the non-default version in our test db.'''
        r = self.fetch('/api/v1/topicversion/2/topics/with_content')
        # Topic-version 2 appends '[early]' to all titles.
        self.assertIn('"standalone_title": "Mathematics [early]"', r)

    @testsize.large()
    def test_topics__library__compact(self):
        r = self.fetch('/api/v1/topics/library/compact')
        self.assertIn('"title": "One Step Equations"', r)

    @testsize.large()
    def test_topicversion__version_id__changelist(self):
        # Test that this requires developer access
        self.assertRaises(urllib2.HTTPError, self.fetch,
                          '/api/v1/topicversion/2/changelist')
        # ...even if it's a non-existent url.
        self.assertRaises(urllib2.HTTPError, self.fetch,
                          '/api/v1/topicversion/10000/changelist')

        self.set_user(developer=True)
        
        # early version
        r = self.fetch('/api/v1/topicversion/2/changelist')
        self.assertIn('TODO(csilvers)', r)

        # later (default) version
        r = self.fetch('/api/v1/topicversion/11/changelist')
        self.assertIn('TODO(csilvers)', r)

        # non-existent version
        r = self.fetch('/api/v1/topicversion/1000/changelist')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__videos(self):
        # Test an early version and a later version.
        r = self.fetch('/api/v1/topicversion/2/topic/basic-equations/videos')
        self.assertIn('"title": "One Step Equations"', r)
        self.assertNotIn('"title": "Exponent Rules Part 1"', r)

        r = self.fetch('/api/v1/topicversion/11/topic/basic-equations/videos')
        self.assertIn('"title": "One Step Equations"', r)
        self.assertNotIn('"title": "Exponent Rules Part 1"', r)

        # Test a topic that doesn't exist in one version.
        r = self.fetch('/api/v1/topicversion/2/topic/art_of_math/videos')
        self.assertIn('TODO(csilvers)', r)        
        r = self.fetch('/api/v1/topicversion/11/topic/art_of_math/videos')
        self.assertIn('TODO(csilvers)', r)

        # Test a super-topic.
        r = self.fetch('/api/v1/topicversion/11/topic/math/videos')
        self.assertIn('TODO(csilvers)', r)

        # Test a topic-version and topic-id that don't exist at all.
        r = self.fetch('/api/v1/topicversion/1000/topic/art_of_math/videos')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/2/topic/does_not_exist/videos')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id__videos(self):
        r = self.fetch('/api/v1/topic/basic-equations/videos')
        self.assertIn('"date_added": "2012-03-28T20:37:54Z"', r)
        self.assertIn('"description": "One Step Equations"', r)
        self.assertIn('"m3u8": "http://s3.amazonaws.com/KA-youtube-converted/'
                      '9DxrF6Ttws4.m3u8/9DxrF6Ttws4.m3u8"', r)
        self.assertNotIn('"mp4": ', r)   # This video is m3u8-only
        self.assertIn('"keywords": "One, Step, Equations, CC_39336_A-REI_3"', r)
        self.assertIn('"views": 43923', r)
        self.assertIn('"youtube_id": "9DxrF6Ttws4"', r)

        r = self.fetch('/api/v1/topic/art_of_math/videos')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__exercises(self):
        # Test an early version and a later version.
        r = self.fetch('/api/v1/topicversion/2/topic/basic-equations/exercises')
        self.assertIn('"display_name": "One step equations"', r)
        self.assertNotIn('"display_name": "Exponent rules"', r)

        r = self.fetch('/api/v1/topicversion/11/topic/basic-equations/exercises')
        self.assertIn('"display_name": "One step equations"', r)
        self.assertNotIn('"display_name": "Exponent rules"', r)

        # And a super-topic with exercises in various sub-topics
        r = self.fetch('/api/v1/topicversion/11/topic/math/exercises')
        self.assertIn('"display_name": "One step equations"', r)
        self.assertIn('"display_name": "Exponent rules"', r)

        # And one with no exercises.
        r = self.fetch('/api/v1/topicversion/11/topic/art/exercises')
        self.assertIn('TODO(csilvers)', r)

        # And one in a non-existent topic-version and topic-id.
        r = self.fetch('/api/v1/topicversion/1000/topic/art_of_math/exercises')
        self.assertIn('TODO(csilvers)', r)

        r = self.fetch('/api/v1/topicversion/2/topic/does_not_exist/exercises')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id__exercises(self):
        r = self.fetch('/api/v1/topic/basic-equations/exercises')
        self.assertIn('"one_step_equations_0.5"', r)
        self.assertIn('"creation_date": "2012-03-28T20:38:50Z"', r)
        self.assertIn('"relative_url": "/exercise/one_step_equations"', r)
        self.assertIn('"short_display_name": "1step eq"', r)
        self.assertIn('"tags": []', r)

    @testsize.large()
    def test_topic__topic_id__progress(self):
        r = self.fetch('/api/v1/topic/basic-equations/progress')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topictree(self):
        r = self.fetch('/api/v1/topicversion/2/topictree')
        # Here we keep track of leading spaces to make sure of indentation.
        self.assertIn('                            '
                      '"short_display_name": "Exp. Rules"', r)
        self.assertIn('                    '
                      '"title": "Exponents (Basic) [early]"', r)
        self.assertIn('                            '
                      '"relative_url": "/video/domain-and-range-1"', r)
        self.assertIn('            '
                      '"title": "Mathematics [early]"', r)
        self.assertNotIn('[late]', r)
        self.assertNotIn('The History of Art in 3 Minutes', r)  # only in v11

        r = self.fetch('/api/v1/topicversion/11/topictree')
        self.assertIn('                            '
                      '"short_display_name": "Exp. Rules"', r)
        self.assertIn('                    '
                      '"title": "Exponents (Basic) [late]"', r)
        self.assertIn('                            '
                      '"relative_url": "/video/domain-and-range-1"', r)
        self.assertIn('            '
                      '"title": "Mathematics [late]"', r)
        self.assertIn('The History of Art in 3 Minutes', r)
        self.assertNotIn('Mathematics of Art', r)  # no hidden topics
        self.assertNotIn('[early]', r)

        r = self.fetch('/api/v1/topicversion/1000/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topictree(self):
        r = self.fetch('/api/v1/topictree')
        # Here we keep track of leading spaces to make sure of indentation.
        self.assertIn('                            '
                      '"display_name": "Exponent rules"',  r)
        self.assertIn('                            '
                      '"display_name": "One step equations"', r)
        self.assertIn('                            '
                      '"title": "Absolute Value 1"', r)
        self.assertIn('            "id": "math"', r)
        self.assertIn('                    "readable_id": '
                      '"courbet--the-artist-s-studio--1854-55"', r)
        self.assertIn('                    '
                      '"title": "The History of Art in 3 Minutes"', r)
        self.assertIn('            "standalone_title": "All About Art"', r)
        self.assertIn('            "title": "Art History [late]"', r)
        self.assertIn('    "title": "The Root of All Knowledge [late]"', r)
        self.assertNotIn('"title": "The Root of All Knowledge [early]"', r)
        self.assertNotIn('Mathematics of Art', r)  # no hidden topics

    @testsize.large()
    def test_dev__topictree__problems(self):
        r = self.fetch('/api/v1/dev/topictree/problems')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__topicversion__version_id__topic__topic_id__topictree(self):
        self.assertRaises(urllib2.HTTPError, self.fetch,
                          '/api/v1/topicversion/2/topic/math/topictree')
        self.set_user(developer=True)
        r = self.fetch('/api/v1/topicversion/2/topic/math/topictree')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/11/topic/math/topictree')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/1000/topic/math/topictree')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/2/topic/does_not_exist/topictree')
        self.assertIn('TODO(csilvers)', r)
        # Try another topic-id, that doesn't have any sub-topics.
        r = self.fetch('/api/v1/topicversion/1000/topic/art/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__topicversion__version_id__topictree(self):
        self.assertRaises(urllib2.HTTPError, self.fetch,
                          '/api/v1/topicversion/2/topictree')
        self.set_user(developer=True)
        r = self.fetch('/api/v1/topicversion/2/topictree')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/11/topictree')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/1000/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__topictree(self):
        self.assertRaises(urllib2.HTTPError, self.fetch,
                          '/api/v1/topictree')
        self.set_user(developer=True)
        r = self.fetch('/api/v1/dev/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__search__query(self):
        r = self.fetch('/api/v1/topicversion/2/search/basic')
        self.assertIn('"title": "Exponents (Basic) [early]"', r)
        self.assertIn('"id": "exponent_rules', r)         # exercise
        self.assertIn('"id": "exponent-rules-part-1', r)  # video
        self.assertIn('"title": "Equations (one-step) [early]"', r)
        self.assertIn('"title": "Domain and Range 1"', r)
        self.assertNotIn('courbet--the-artist-s-studio--1854-55', r)

        r = self.fetch('/api/v1/topicversion/11/search/basic')
        self.assertIn('"title": "Exponents (Basic) [late]"', r)
        self.assertIn('"id": "exponent_rules', r)         # exercise
        self.assertIn('"id": "exponent-rules-part-1', r)  # video
        self.assertIn('"title": "Equations (one-step) [late]"', r)
        self.assertIn('"title": "Domain and Range 1"', r)
        self.assertNotIn('courbet--the-artist-s-studio--1854-55', r)

        r = self.fetch('/api/v1/topicversion/11/search/Studio')
        self.assertNotIn('"title": "Exponents (Basic) [late]"', r)
        self.assertIn('courbet--the-artist-s-studio--1854-55', r)

        # This should only match for topicversion 11, not 2.
        r = self.fetch('/api/v1/topicversion/2/search/Minutes')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/11/search/Minutes')
        self.assertIn('TODO(csilvers)', r)
        # Gives no results
        r = self.fetch('/api/v1/topicversion/11/search/NadaNothingZilch')
        self.assertIn('TODO(csilvers)', r)
        # Try an invalid topic-version
        r = self.fetch('/api/v1/topicversion/1000/search/Minutes')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id(self):
        r = self.fetch('/api/v1/topicversion/2/topic/math')
        self.assertIn('"title": "Exponents (Basic) [early]"', r)
        self.assertIn('"title": "Equations (one-step) [early]"', r)
        self.assertIn('"title": "Other [early]"', r)
        self.assertIn('"standalone_title": "All About Math"', r)
        self.assertNotIn('[late]', r)

        r = self.fetch('/api/v1/topicversion/11/topic/math')
        self.assertIn('"title": "Exponents (Basic) [late]"', r)
        self.assertIn('"title": "Equations (one-step) [late]"', r)
        self.assertIn('"title": "Other [late]"', r)
        self.assertIn('"standalone_title": "All About Math"', r)
        self.assertNotIn('[early]', r)

        r = self.fetch('/api/v1/topicversion/1000/topic/math')
        self.assertIn('TODO(csilvers)', r)

        r = self.fetch('/api/v1/topicversion/2/topic/does_not_exist')
        self.assertIn('TODO(csilvers)', r)

        # Try another topic-id, that doesn't have any sub-topics.
        r = self.fetch('/api/v1/topicversion/1000/topic/art')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id(self):
        r = self.fetch('/api/v1/topic/math')
        self.assertIn('"children":', r)
        self.assertIn('"id": "basic-exponents"', r)
        self.assertIn('"title": "Exponents (Basic) [late]"', r)
        self.assertNotIn('"title": "Exponents (Basic) [early]"', r)
        self.assertIn('"description": "A super-topic I made up for this test"',
                      r)
        self.assertIn('"topic_page_url": "/math"', r)

        r = self.fetch('/api/v1/topic/does_not_exist')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__topic_page(self):
        # Test an early version and a later version.
        r = self.fetch('/api/v1/topicversion/2/topic/basic-equations/topic-page')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/11/topic/basic-equations/topic-page')
        self.assertIn('TODO(csilvers)', r)
        # Test a topic that doesn't exist in one version.
        r = self.fetch('/api/v1/topicversion/2/topic/art_of_math/topic-page')
        self.assertIn('TODO(csilvers)', r)        
        r = self.fetch('/api/v1/topicversion/11/topic/art_of_math/topic-page')
        self.assertIn('TODO(csilvers)', r)
        # Test a super-topic.
        r = self.fetch('/api/v1/topicversion/11/topic/math/topic-page')
        self.assertIn('TODO(csilvers)', r)
        # Test a topic-version and topic-id that don't exist at all.
        r = self.fetch('/api/v1/topicversion/1000/topic/art_of_math/topic-page')
        self.assertIn('TODO(csilvers)', r)
        r = self.fetch('/api/v1/topicversion/2/topic/does_not_exist/topic-page')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id__topic_page(self):
        r = self.fetch('/api/v1/topic/<topic_id>/topic-page')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__maplayout(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/maplayout')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_maplayout(self):
        r = self.fetch('/api/v1/maplayout')
        self.assertIn('"icon_url": '
                      '"/images/power-mode/badges/default-40x40.png"', r)
        self.assertIn('"id": "basic-equations"', r), 
        self.assertIn('"standalone_title": "One-Step Equations"', r)
        self.assertIn('"x": 1', r)
        self.assertIn('"y": 6', r)
        self.assertIn('"id": "basic-exponents"', r), 

    @testsize.large()
    def test_topicversion__default__id(self):
        r = self.fetch('/api/v1/topicversion/default/id')
        self.assertEqual('11', r)

    @testsize.large()
    def test_dev__task_message(self):
        r = self.fetch('/api/v1/dev/task_message')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__children(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/topic/<topic_id>/children')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id__children(self):
        r = self.fetch('/api/v1/topic/<topic_id>/children')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__setdefault(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/setdefault')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversions__(self):
        r = self.fetch('/api/v1/topicversions/')
        self.assertIn('"copied_from_number": 11', r)
        self.assertIn('"number": 12', r)
        self.assertIn('"created_on": "2012-04-13T16:59:30Z"', r)
        self.assertIn('"number": 11', r)
        self.assertIn('"updated_on": "2012-04-13T16:59:27', r)
        self.assertIn('"copied_from_number": null', r)
        self.assertIn('"number": 2', r)
        self.assertIn('"made_default_on": "2012-03-29T02:02:54Z"', r)
        self.assertIn('"last_edited_by": "http://nouserid.khanacademy.org/'
                      '365d6b6ca0f261d1b3c1975d4343f826"', r)

    @testsize.large()
    def test_topicversion__version_id__unused_content(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/unused_content')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__url__url_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/url/<url_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_url__url_id(self):
        r = self.fetch('/api/v1/url/<url_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__video_id__explore_url(self):
        r = self.fetch('/api/v1/videos/<video_id>/explore_url')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_exercises(self):
        r = self.fetch('/api/v1/exercises')
        self.assertIn('"exponents_2"', r)
        self.assertIn('"creation_date": "2012-03-28T20:38:49Z"', r)
        self.assertIn('"one_step_equations_0.5"', r)
        self.assertIn('"display_name": "One step equations"', r)
        self.assertIn('"short_display_name": "1step eq"', r)
        self.assertIn('"tags": []', r)


    @testsize.large()
    def test_topicversion__version_id__exercises__exercise_name(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/exercises/<exercise_name>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_exercises__exercise_name(self):
        r = self.fetch('/api/v1/exercises/<exercise_name>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_exercises__recent(self):
        r = self.fetch('/api/v1/exercises/recent')
        # TODO(csilvers): mock out the clock for this, so one of the
        # exercises is recent but the other isn't.
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_exercises__exercise_name__followup_exercises(self):
        r = self.fetch('/api/v1/exercises/<exercise_name>/followup_exercises')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_exercises__exercise_name__videos(self):
        r = self.fetch('/api/v1/exercises/<exercise_name>/videos')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__videos__video_id(self):
        r = self.fetch('/api/v1/topicversion/<version_id>/videos/<video_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__video_id(self):
        r = self.fetch('/api/v1/videos/<video_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__recent(self):
        # TODO(csilvers): mock out time so we can test this
        r = self.fetch('/api/v1/videos/recent')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__video_id__exercises(self):
        r = self.fetch('/api/v1/videos/<video_id>/exercises')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__topic_id__video_id__play(self):
        r = self.fetch('/api/v1/videos/<topic_id>/<video_id>/play')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_commoncore(self):
        r = self.fetch('/api/v1/commoncore')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__youtube_id__youtubeinfo(self):
        r = self.fetch('/api/v1/videos/<youtube_id>/youtubeinfo')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user(self):
        '''Test that the result is json and has the appropriate fields.'''
        r = self.fetch('/api/v1/user')    
        self.assertIn('user_id', r)

    @testsize.large()
    def test_user__username_available(self):
        r = self.fetch('/api/v1/user/username_available')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__promo__promo_name(self):
        r = self.fetch('/api/v1/user/promo/<promo_name>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__profile(self):
        r = self.fetch('/api/v1/user/profile')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__coaches(self):
        r = self.fetch('/api/v1/user/coaches')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__students(self):
        r = self.fetch('/api/v1/user/students')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__studentlists(self):
        r = self.fetch('/api/v1/user/studentlists')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__videos(self):
        r = self.fetch('/api/v1/user/videos')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__videos__youtube_id(self):
        r = self.fetch('/api/v1/user/videos/<youtube_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__videos__youtube_id__log_compatability(self):
        r = self.fetch('/api/v1/user/videos/<youtube_id>/log_compatability')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__topic__topic_id__exercises__next(self):
        r = self.fetch('/api/v1/user/topic/<topic_id>/exercises/next')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises(self):
        r = self.fetch('/api/v1/user/exercises')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__topic__topic_id__exercises(self):
        r = self.fetch('/api/v1/user/topic/<topic_id>/exercises')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__students__progress__summary(self):
        r = self.fetch('/api/v1/user/students/progress/summary')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name(self):
        r = self.fetch('/api/v1/user/exercises/<exercise_name>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name__followup_exercises(self):
        r = self.fetch('/api/v1/user/exercises/<exercise_name>/followup_exercises')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__topics(self):
        r = self.fetch('/api/v1/user/topics')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__topic__topic_id(self):
        r = self.fetch('/api/v1/user/topic/<topic_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__reviews__count(self):
        r = self.fetch('/api/v1/user/exercises/reviews/count')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name__log(self):
        r = self.fetch('/api/v1/user/exercises/<exercise_name>/log')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__videos__youtube_id__log(self):
        r = self.fetch('/api/v1/user/videos/<youtube_id>/log')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_badges(self):
        r = self.fetch('/api/v1/badges')
        self.assertIn('"icon_src": "/images/badges/sun-small.png"', r)
        self.assertIn('"badge_category": 3', r)

    @testsize.large()
    def test_badges__categories(self):
        r = self.fetch('/api/v1/badges/categories')
        self.assertIn('"icon_src": "/images/badges/sun-small.png"', r)
        self.assertIn('"category": 3', r)

    @testsize.large()
    def test_badges__categories__category(self):
        r = self.fetch('/api/v1/badges/categories/<category>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__badges(self):
        r = self.fetch('/api/v1/user/badges')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__activity(self):
        r = self.fetch('/api/v1/user/activity')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_autocomplete(self):
        r = self.fetch('/api/v1/autocomplete')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__backupmodels(self):
        r = self.fetch('/api/v1/dev/backupmodels')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__protobufquery(self):
        r = self.fetch('/api/v1/dev/protobufquery')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__protobuf__entity(self):
        r = self.fetch('/api/v1/dev/protobuf/<entity>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__problems(self):
        r = self.fetch('/api/v1/dev/problems')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__videos(self):
        r = self.fetch('/api/v1/dev/videos')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__users(self):
        r = self.fetch('/api/v1/dev/users')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__students__progressreport(self):
        r = self.fetch('/api/v1/user/students/progressreport')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals(self):
        r = self.fetch('/api/v1/user/goals')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals__current(self):
        r = self.fetch('/api/v1/user/goals/current')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__students__goals(self):
        r = self.fetch('/api/v1/user/students/goals')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals__id(self):
        r = self.fetch('/api/v1/user/goals/<id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_avatars(self):
        r = self.fetch('/api/v1/avatars')
        self.assertIn('"image_src": "/images/avatars/leaf-green.png"', r)

    @testsize.large()
    def test_dev__version(self):
        r = self.fetch('/api/v1/dev/version')
        self.assertIn('"version_id": "', r)


class V1EndToEndDeleteTest(V1EndToEndTestBase):
    '''Test all the DELETE methods in v1.py.'''
    def setUp(self):
        # TODO(csilvers): reset the database before each of these.
        super(V1EndToEndDeleteTest, self).setUp()
        self.method = 'DELETE'

    @testsize.large()
    def test_user__studentlists__list_key(self):
        r = self.fetch('/api/v1/user/studentlists/list_key>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals__id(self):
        r = self.fetch('/api/v1/user/goals/id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals(self):
        r = self.fetch('/api/v1/user/goals')
        self.assertIn('TODO(csilvers)', r)


class V1EndToEndPostTest(V1EndToEndTestBase):
    '''Test all the POST methods in v1.py.'''
    def setUp(self):
        # TODO(csilvers): reset the database before each of these.
        super(V1EndToEndPostTest, self).setUp()
        self.method = 'POST'

    # Note some of these also accept PUT, but we don't seem to distinguish.

    @testsize.large()
    def test_topicversion__version_id__exercises__exercise_name(self):
        r = self.fetch('/api/v1/topicversion/version_id/exercises/exercise_name>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__videos__(self):
        r = self.fetch('/api/v1/topicversion/version_id/videos/')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__videos__video_id(self):
        r = self.fetch('/api/v1/topicversion/version_id/videos/video_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__profile(self):
        r = self.fetch('/api/v1/user/profile')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__badges__public(self):
        r = self.fetch('/api/v1/user/badges/public')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_parentsignup(self):
        r = self.fetch('/api/v1/parentsignup')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__(self):
        r = self.fetch('/api/v1/videos/')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__video_id(self):
        r = self.fetch('/api/v1/videos/video_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__deletechange(self):
        r = self.fetch('/api/v1/topicversion/version_id/deletechange')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__parent_id__addchild(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/parent_id/addchild')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__parent_id__addchild(self):
        r = self.fetch('/api/v1/topic/parent_id/addchild')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__parent_id__deletechild(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/parent_id/deletechild')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__parent_id__deletechild(self):
        r = self.fetch('/api/v1/topic/parent_id/deletechild')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__old_parent_id__movechild(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/old_parent_id/movechild')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__old_parent_id__movechild(self):
        r = self.fetch('/api/v1/topic/old_parent_id/movechild')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id__ungroup(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/topic_id/ungroup')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id__ungroup(self):
        r = self.fetch('/api/v1/topic/topic_id/ungroup')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__video_id__download_available(self):
        r = self.fetch('/api/v1/videos/video_id/download_available')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__promo__promo_name(self):
        r = self.fetch('/api/v1/user/promo/promo_name>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__studentlists(self):
        r = self.fetch('/api/v1/user/studentlists')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__videos__youtube_id__log(self):
        r = self.fetch('/api/v1/user/videos/youtube_id/log')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name__problems__problem_number__attempt(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/problems/problem_number/attempt')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name__problems__problem_number__hint(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/problems/problem_number/hint')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name__reset_streak(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/reset_streak')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__exercises__exercise_name__wrong_attempt(self):
        r = self.fetch('/api/v1/user/exercises/exercise_name/wrong_attempt')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_developers__add(self):
        r = self.fetch('/api/v1/developers/add')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_developers__remove(self):
        r = self.fetch('/api/v1/developers/remove')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_coworkers__add(self):
        r = self.fetch('/api/v1/coworkers/add')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_coworkers__remove(self):
        r = self.fetch('/api/v1/coworkers/remove')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals(self):
        r = self.fetch('/api/v1/user/goals')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_exercises__exercise_name(self):
        r = self.fetch('/api/v1/exercises/exercise_name>')
        self.assertIn('TODO(csilvers)', r)


class V1EndToEndPutTest(V1EndToEndTestBase):
    '''Test all the PUT methods in v1.py.'''
    def setUp(self):
        # TODO(csilvers): reset the database before each of these.
        super(V1EndToEndPutTest, self).setUp()
        self.method = 'PUT'

    @testsize.large()
    def test_dev__topicversion__version_id__topic__topic_id__topictree(self):
        r = self.fetch('/api/v1/dev/topicversion/version_id/topic/topic_id/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__topicversion__version_id__topictree(self):
        r = self.fetch('/api/v1/dev/topicversion/version_id/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__topictree__init__publish(self):
        r = self.fetch('/api/v1/dev/topictree/init/publish>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_dev__topictree(self):
        r = self.fetch('/api/v1/dev/topictree')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__topic__topic_id(self):
        r = self.fetch('/api/v1/topicversion/version_id/topic/topic_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topic__topic_id(self):
        r = self.fetch('/api/v1/topic/topic_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__maplayout(self):
        r = self.fetch('/api/v1/topicversion/version_id/maplayout')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_maplayout(self):
        r = self.fetch('/api/v1/maplayout')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id(self):
        r = self.fetch('/api/v1/topicversion/version_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__url__(self):
        r = self.fetch('/api/v1/topicversion/version_id/url/')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_topicversion__version_id__url__url_id(self):
        r = self.fetch('/api/v1/topicversion/version_id/url/url_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_url__(self):
        r = self.fetch('/api/v1/url/')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_url__url_id(self):
        r = self.fetch('/api/v1/url/url_id>')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_videos__video_id__explore_url(self):
        r = self.fetch('/api/v1/videos/video_id/explore_url')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__coaches(self):
        r = self.fetch('/api/v1/user/coaches')
        self.assertIn('TODO(csilvers)', r)

    @testsize.large()
    def test_user__goals__id(self):
        r = self.fetch('/api/v1/user/goals/id>')
        self.assertIn('TODO(csilvers)', r)
