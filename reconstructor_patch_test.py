from __future__ import with_statement

from agar.test.base_test import BaseTest

import models # needed for side-effects
from goals.models import *
from reconstructor_patch import ReconstructorPatch

import pickle


class ReconstructorTest(BaseTest):
    def setUp(self):
        super(ReconstructorTest, self).setUp()

        self.busted = "(lp1\nccopy_reg\n_reconstructor\np2\n(cgoals.models\nGoalObjectiveExerciseProficiency\np3\nc__builtin__\nobject\np4\nNtRp5\n(dp6\nS'exercise_name'\np7\nVdivisibility\np8\nsS'description'\np9\nVDivisibility\np10\nsS'progress'\np11\nF0\nsbag2\n(g3\ng4\nNtRp12\n(dp13\ng7\nVadding_and_subtracting_fractions\np14\nsg9\nVAdding and subtracting fractions\np15\nsg11\nF1\nsbag2\n(g3\ng4\nNtRp16\n(dp17\ng7\nVconverting_repeating_decimals_to_fractions_2\np18\nsg9\nVConverting repeating decimals to fractions 2\np19\nsg11\nF0.21781389974011148\nsbag2\n(cgoals.models\nGoalObjectiveWatchVideo\np20\ng4\nNtRp21\n(dp22\nS'video_key'\np23\ng2\n(cgoogle.appengine.api.datastore_types\nKey\np24\ng4\nNtRp25\n(dp26\nS'_Key__reference'\np27\ng2\n(cgoogle.appengine.datastore.entity_pb\nReference\np28\ng4\nNtRp29\nS'j\\x0es~khan-academyr\\x0f\\x0b\\x12\\x05Video\\x18\\xe7\\x8a\\xa8\\x8b\\x01\\x0c'\nbsS'_str'\np30\nNsbsS'video_readable_id'\np31\nV30-60-90-triangle-side-ratios-proof\np32\nsg9\nV30-60-90 Triangle Side Ratios Proof\np33\nsg11\nF0\nsba."
        self.working = "(lp0\nccopy_reg\n_reconstructor\np1\n(cgoals.models\nGoalObjectiveExerciseProficiency\np2\nc__builtin__\nobject\np3\nNtp4\nRp5\n(dp6\nS'exercise_name'\np7\nVsimplifying_fractions\np8\nsS'description'\np9\nVSimplifying fractions\np10\nsS'progress'\np11\nF0.0\nsbag1\n(g2\ng3\nNtp12\nRp13\n(dp14\ng7\nVadding_and_subtracting_polynomials\np15\nsg9\nVAdding and subtracting polynomials\np16\nsg11\nF0.0\nsbag1\n(g2\ng3\nNtp17\nRp18\n(dp19\ng7\nVconverting_repeating_decimals_to_fractions_2\np20\nsg9\nVConverting repeating decimals to fractions 2\np21\nsg11\nF0.0\nsbag1\n(cgoals.models\nGoalObjectiveWatchVideo\np22\ng3\nNtp23\nRp24\n(dp25\nS'video_key'\np26\ng1\n(cgoogle.appengine.api.datastore_types\nKey\np27\ng3\nNtp28\nRp29\n(dp30\nS'_Key__reference'\np31\n(igoogle.appengine.datastore.entity_pb\nReference\np32\nS'j\\x0es~khan-academyr\\x0f\\x0b\\x12\\x05Video\\x18\\xe7\\x8a\\xa8\\x8b\\x01\\x0c'\np34\nbsS'_str'\np35\nNsbsS'video_readable_id'\np36\nV30-60-90-triangle-side-ratios-proof\np37\nsg9\nV30-60-90 Triangle Side Ratios Proof\np38\nsg11\nF0.0\nsba."

    def test_patch_should_not_affect_normal_operation(self):
        obj = pickle.loads(self.working)
        self.assertEqual(list, type(obj))

        with ReconstructorPatch():
            # make sure this still works with our monkey patched reconstructor
            obj = pickle.loads(self.working)
            self.assertIsInstance(obj, list)

    def test_patch_should_depickle_new_style_refs(self):
        # first make sure that the busted one doesn't work
        with self.assertRaises(TypeError):
            obj = pickle.loads(self.busted)

        with ReconstructorPatch():
            # finally try to load busted again with the patched versions
            obj = pickle.loads(self.busted)
            self.assertIsInstance(obj, list)
