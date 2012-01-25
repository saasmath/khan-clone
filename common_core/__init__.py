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
    def post(self):
        self.get()

    def get(self):
        self.redirect("/api/v1/commoncore")
        return

