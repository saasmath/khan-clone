from __future__ import absolute_import
import os
import logging

import user_util
from google.appengine.ext.webapp import template
from coach_resources import util_coach

from .models import CommonCoreMap

class CommonCore(util_coach.CoachResourcesRequestHandler):

    @user_util.open_access
    def get(self):
        cc_map = CommonCoreMap.get_all_structured(lightweight=True)
        
        grade_totals = {} # Number of unique [exercise | videos] applying to each grade
        
        for grade in cc_map:
            video_set = set([])
            exercise_set = set([])
            
            for domain in grade['domains']:
                for standard in domain['standards']:
                    for exercise in standard['exercises']: exercise_set.add(exercise['display_name'])
                    for video in standard['videos']: video_set.add(video['title'])
            
            grade_total = {'videos' : len(video_set), 'exercises' : len(exercise_set)}
            grade_totals[grade['grade']] = grade_total
                
        
        self.render_jinja2_template('coach_resources/view_map.html', {'cc_map' : cc_map, 'grade_totals' : grade_totals, "selected_id": "commoncore"})

