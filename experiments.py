#!/usr/bin/env python

from gae_bingo.gae_bingo import ab_test, find_alternative_for_user
from gae_bingo.models import ConversionTypes

class StrugglingExperiment(object):

    DEFAULT = 'old'

    # "Struggling" model experiment parameters.
    _ab_test_alternatives = {
        'old': 8, # The original '>= 20 problems attempted' heuristic
        'accuracy_1.8': 1, # Using an accuracy model with 1.8 as the parameter
        'accuracy_2.0': 1, # Using an accuracy model with 2.0 as the parameter
    }
    _conversion_tests = [
        ('struggling_problems_done', ConversionTypes.Counting),
        ('struggling_problems_wrong', ConversionTypes.Counting),
        ('struggling_problems_correct', ConversionTypes.Counting),
        ('struggling_gained_proficiency_all', ConversionTypes.Counting),
        ('struggling_gained_proficiency_post_struggling', ConversionTypes.Counting),

        # the user closed the "Need help?" dialog that pops up
        ('struggling_message_dismissed', ConversionTypes.Counting),

        # the user clicked on the video in the "Need help?" dialog that pops up
        ('struggling_videos_clicked_post_struggling', ConversionTypes.Counting),

        # the user clicked on the pre-requisite exercise in the
        # "Need help?" dialog that pops up
        ('struggling_prereq_clicked_post_struggling', ConversionTypes.Counting),

        ('struggling_videos_landing', ConversionTypes.Counting),
        ('struggling_videos_finished', ConversionTypes.Counting),
        # the number of users that went into struggling at some point
        ('struggling_struggled_binary', ConversionTypes.Binary),
    ]
    _conversion_names, _conversion_types = [
        list(x) for x in zip(*_conversion_tests)]


    @staticmethod
    def get_alternative_for_user(user_data, current_user=False):
        """ Returns the experiment alternative for the specified user, or
        the current logged in user. If the user is the logged in user, will
        opt in for an experiment, as well. Will not affect experiments if
        not the current user.
        
        """
        
        # We're interested in analyzing the effects of different struggling
        # models on users. A more accurate model would imply that the user
        # can get help earlier on. This varies drastically for those with
        # and without coaches, so it is useful to separate the population out.
        if user_data.coaches:
            exp_name = 'Struggling model 2 (w/coach)'
        else:
            exp_name = 'Struggling model 2 (no coach)'

        # If it's not the current user, then it must be an admin or coach
        # viewing a dashboard. Don't affect the actual experiment as only the
        # actions of the user affect her participation in the experiment.
        if current_user:
            return ab_test(exp_name,
                       	   StrugglingExperiment._ab_test_alternatives,
                       	   StrugglingExperiment._conversion_names,
                           StrugglingExperiment._conversion_types)

        return find_alternative_for_user(exp_name, user_data)


class InteractiveTranscriptExperiment(object):

    NAME = 'Interactive transcript on video page'

    NO_SHOW = 'no_show'
    SHOW = 'show'

    _ab_test_alternatives = [
        NO_SHOW,  # Don't show interactive transcript
        SHOW,  # Show interactive transcript
    ]

    _conversion_tests = [
        # server-side conversions
        ('videos_landing', ConversionTypes.Counting),
        ('videos_finished', ConversionTypes.Counting),

        # client-side conversions to gauge interaction with the transcript
        ('interactive_transcript_shown', ConversionTypes.Counting),
        ('interactive_transcript_shown_binary', ConversionTypes.Binary),
        ('interactive_transcript_subtitle_click', ConversionTypes.Counting),
        ('interactive_transcript_subtitle_click_binary', ConversionTypes.Binary),
    ]

    _conversion_names, _conversion_types = [
        list(x) for x in zip(*_conversion_tests)]

    @staticmethod
    def ab_test():
        """gaebingo.ab_test() wrapper"""
        return ab_test(InteractiveTranscriptExperiment.NAME,
                       InteractiveTranscriptExperiment._ab_test_alternatives,
                       InteractiveTranscriptExperiment._conversion_names,
                       InteractiveTranscriptExperiment._conversion_types)
