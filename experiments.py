#!/usr/bin/env python

from gae_bingo.gae_bingo import ab_test
from gae_bingo.models import ConversionTypes

class StrugglingExperiment(object):

    # "Struggling" model experiment parameters.
    _ab_test_alternatives = {
        'old': 8, # The original '>= 20 problems attempted' heuristic
        'accuracy_1.8': 1, # Using an accuracy model with 1.8 as the parameter
        'accuracy_2.0': 1, # Using an accuracy model with 2.0 as the parameter
    }
    _conversion_tests = [
        ('struggling_problems_done', ConversionTypes.Counting),
        ('struggling_problems_done_post_struggling', ConversionTypes.Counting),
        ('struggling_problems_wrong', ConversionTypes.Counting),
        ('struggling_problems_wrong_post_struggling', ConversionTypes.Counting),
        ('struggling_problems_correct', ConversionTypes.Counting),
        ('struggling_problems_correct_post_struggling', ConversionTypes.Counting),
        ('struggling_gained_proficiency_all', ConversionTypes.Counting),

        # the user closed the "Need help?" dialog that pops up
        ('struggling_message_dismissed', ConversionTypes.Counting),

        # the user clicked on the video in the "Need help?" dialog that pops up
        ('struggling_videos_clicked_post_struggling', ConversionTypes.Counting),
        ('struggling_videos_landing', ConversionTypes.Counting),
        ('struggling_videos_finished', ConversionTypes.Counting),
    ]
    _conversion_names, _conversion_types = [
        list(x) for x in zip(*_conversion_tests)]


    @staticmethod
    def get_alternative_for_user(user_data):
        # We're interested in analyzing the effects of different struggling
        # models on users. A more accurate model would imply that the user
        # can get help earlier on. This varies drastically for those with and
        # without coaches, so it is useful to separate the population out.
        if user_data.coaches:
            return ab_test('Struggling model (w/coach)',
                       	   StrugglingExperiment._ab_test_alternatives,
                       	   StrugglingExperiment._conversion_names,
                           StrugglingExperiment._conversion_types,
                           user_data = user_data)
        else:
            return ab_test('Struggling model (no coach)',
                           StrugglingExperiment._ab_test_alternatives,
                           StrugglingExperiment._conversion_names,
                           StrugglingExperiment._conversion_types,
                           user_data = user_data)
