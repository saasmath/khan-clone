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
        
        self.render_jinja2_template('commoncore/view_map.html', {'cc_map' : cc_map})

