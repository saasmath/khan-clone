#import os, logging
#
#from google.appengine.ext import db, deferred
#from google.appengine.api import users
import user_util
#import util
#from app import App
#from models import UserData
#from common_core.models import CommonCoreMap
import request_handler
#import itertools
#from api.auth.xsrf import ensure_xsrf_cookie

#import gdata.youtube
#import gdata.youtube.data
#import gdata.youtube.service
#import urllib
#import csv
#import StringIO

class MapLayoutEditor(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        self.render_jinja2_template('kmap_editor/kmap_editor.html', {})

