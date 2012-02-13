from __future__ import absolute_import
import os
import simplejson as json
import datetime
import math
import logging
import urllib, urllib2
import csv
import StringIO

from request_handler import RequestHandler
from app import App
from user_util import developer_only
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import mail

from .models import CommonCoreMap

class CommonCore(RequestHandler):

    def get(self):
        f = open('common_core/data/ccmap.json', 'rb')
        cc_map = json.loads(f.read())
        
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
                
        
        self.render_jinja2_template('commoncore/view_map.html', {'cc_map' : cc_map, 'grade_totals' : grade_totals})

