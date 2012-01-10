import os, logging

from google.appengine.ext import db
from google.appengine.api import users
import util
from app import App
from models import UserData
import request_handler
import user_util
import itertools
from api.auth.xsrf import ensure_xsrf_cookie

import gdata.youtube
import gdata.youtube.data
import gdata.youtube.service
import urllib
import csv

class Panel(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        self.render_jinja2_template('devpanel/panel.html', { "selected_id": "panel" })

class MergeUsers(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):

        source_email = self.request_string("source_email")
        target_email = self.request_string("target_email")

        source_description = ""
        target_description = ""

        source = UserData.get_from_user_input_email(source_email)
        target = UserData.get_from_user_input_email(target_email)

        template_values = {
                "selected_id": "users",
                "source_email": source_email,
                "target_email": target_email,
                "source": source,
                "target": target,
                "merged": self.request_bool("merged", default=False),
        }

        self.render_jinja2_template("devpanel/mergeusers.html", template_values)

    @user_util.developer_only
    def post(self):

        if not self.request_bool("confirm", default=False):
            self.get()
            return

        source = self.request_user_data("source_email")
        target = self.request_user_data("target_email")

        merged = False

        if source and target:

            old_source_email = source.email

            # Make source the new official user, because it has all the historical data.
            # Just copy over target's identifying properties.
            source.current_user = target.current_user
            source.user_email = target.user_email
            source.user_nickname = target.user_nickname
            source.user_id = target.user_id

            # Put source, which gives it the same identity as target 
            source.put()

            # Delete target
            target.delete()

            self.redirect("/admin/emailchange?merged=1&source_email=%s&target_email=%s" % (old_source_email, target.email))
            return

        self.redirect("/admin/emailchange")

        
class Manage(request_handler.RequestHandler):

    @user_util.admin_only # only admins may add devs, devs cannot add devs
    @ensure_xsrf_cookie
    def get(self):
        developers = UserData.all()
        developers.filter('developer = ', True).fetch(1000)
        template_values = { 
            "developers": developers,
            "selected_id": "devs",
        }

        self.render_jinja2_template('devpanel/devs.html', template_values) 
        
class ManageCoworkers(request_handler.RequestHandler):

    @user_util.developer_only
    @ensure_xsrf_cookie
    def get(self):

        user_data_coach = self.request_user_data("coach_email")
        user_data_coworkers = []

        if user_data_coach:
            user_data_coworkers = user_data_coach.get_coworkers_data()

        template_values = {
            "user_data_coach": user_data_coach,
            "user_data_coworkers": user_data_coworkers,
            "selected_id": "coworkers",
        }

        self.render_jinja2_template("devpanel/coworkers.html", template_values)
        
class CommonCore(request_handler.RequestHandler):
    
    @user_util.developer_only
    def get(self):
        
        cc_videos = []
        cc_file = "common_core/"
        auth_sub_url = ""
        
        token = self.request_string("token")
        
        if token: # AuthSub token from YouTube API - load and tag videos            
            
            # default for yt_user is test account khanacademyschools
            
            yt_account = self.request_string("account") if self.request_string("account") else "khanacademyschools"
            
            logging.info("****Youtube Account: " + yt_account)
            
            cc_file += "cc_video_mapping.csv" if yt_account == "khanacademy" else "test_data.csv"
            
            yt_service = gdata.youtube.service.YouTubeService()
            yt_service.SetAuthSubToken(token)
            yt_service.UpgradeToSessionToken()
            yt_service.developer_key = 'AI39si6eFsAasPBlI_xQLee6-Ii70lrEhGAXn_ryCSWQdMP8xW67wkawIjDYI_XieWc0FsdsH5HMPPpvenAtaEl5fCLmHX8A5w'
            
            f = open(cc_file, 'U')
            reader = csv.DictReader(f, dialect='excel')
            
            for record in reader:
                
                if record["youtube_id"] and not record["youtube_id"] == "#N/A":
                    
                    entry = yt_service.GetYouTubeVideoEntry(video_id=record["youtube_id"])
                    
                    # if entry and record["keyword"] not in entry.media.keywords.text:
                    if entry:
                                    
                        keywords = entry.media.keywords.text or "" 
                                    
                        entry.media.keywords.text = keywords + "," + record["keyword"]
                        video_url = "https://gdata.youtube.com/feeds/api/users/"+ yt_account + "/uploads/" + record["youtube_id"]
                        
                        try:
                            updated_entry = yt_service.UpdateVideoEntry(entry, video_url)
                            logging.info("***PROCESSED*** Title: " + entry.media.title.text + " | Keywords: " + entry.media.keywords.text)
                            cc_videos.append(record)
                        except Exception, e:
                            logging.warning("***FAILED update*** Title: " + record["title"] + ", ID: " + record["youtube_id"], "\n" + e)                            
                        
            f.close() 
            
        else:         
            params = {
                'next': self.request.url,
                'scope': "http://gdata.youtube.com", 
                'session': "1", 
                'secure': "0"
            }

            base_url = "https://www.google.com/accounts/AuthSubRequest?"
            auth_sub_url = base_url + urllib.urlencode(params)
                 
        template_values = {
            "token" : token,
            "cc_videos" : cc_videos,
            "auth_sub_url" : auth_sub_url,
            "selected_id": "commoncore",
        }
        
        self.render_jinja2_template("devpanel/commoncore.html", template_values)
