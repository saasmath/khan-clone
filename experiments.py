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

class SuggestedActivityExperiment(object):

    NO_SHOW = 'no_show'
    SHOW = 'show'

    _ab_test_alternatives = {
        NO_SHOW: 5, # Don't show suggested activity
        SHOW: 5, # Show suggested activity
    }
    _conversion_tests = [
        # TODO: Allow experiments to share common conversions
        # instead of repeating them as below
        ('suggested_activity_problems_done', ConversionTypes.Counting),
        ('suggested_activity_problems_wrong', ConversionTypes.Counting),
        ('suggested_activity_problems_correct', ConversionTypes.Counting),
        ('suggested_activity_gained_proficiency_all', ConversionTypes.Counting),

        ('suggested_activity_videos_landing', ConversionTypes.Counting),
        ('suggested_activity_videos_landing_binary', ConversionTypes.Binary),
        ('suggested_activity_videos_finished', ConversionTypes.Counting),

        ('suggested_activity_exercises_landing', ConversionTypes.Counting),
        ('suggested_activity_visit_suggested_exercise', ConversionTypes.Counting),

        ('suggested_activity_visit_profile', ConversionTypes.Counting),

        # Clicks on suggested activities on the profile page
        ('suggested_activity_click_through_exercise', ConversionTypes.Counting),
        ('suggested_activity_click_through_video', ConversionTypes.Counting),
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
        exp_name = "Suggested activity on profile page"

        # If it's not the current user, then it must be an admin or coach
        # viewing a dashboard. Don't affect the actual experiment as only the
        # actions of the user affect her participation in the experiment.
        if current_user:
            return ab_test(exp_name,
                           SuggestedActivityExperiment._ab_test_alternatives,
                           SuggestedActivityExperiment._conversion_names,
                           SuggestedActivityExperiment._conversion_types)

        return find_alternative_for_user(exp_name, user_data)

class HintsExperiment(object):
    # These conversion tests are left available for anyone else to pass into
    # a call to gae_bingo.ab_test as useful hints AB signals.
    _hints_conversion_tests = [
        ('hints_free_hint', ConversionTypes.Counting),
        ('hints_free_hint_binary', ConversionTypes.Binary),
        ('hints_costly_hint', ConversionTypes.Counting),
        ('hints_costly_hint_binary', ConversionTypes.Binary),
        ('hints_problems_done', ConversionTypes.Counting),
        ('hints_gained_proficiency_all', ConversionTypes.Counting),
        ('hints_gained_new_proficiency', ConversionTypes.Counting),
        ('hints_gained_proficiency_easy_binary', ConversionTypes.Binary),
        ('hints_gained_proficiency_hard_binary', ConversionTypes.Binary),
        ('hints_wrong_problems', ConversionTypes.Counting),
        ('hints_keep_going_after_wrong', ConversionTypes.Counting),
    ]
    _hints_conversion_names, _hints_conversion_types = [
        list(x) for x in zip(*_hints_conversion_tests)]
