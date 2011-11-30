import request_handler
import user_util
import cgi
import re
import urllib
import logging
from google.appengine.ext import db


import models
from models import Topic, Playlist, Video

class EditTaxonomy(request_handler.RequestHandler):

    def get_tree_html(self, t):
        html = "<ul>"
        html += self.get_tree_node_html(t)
        html += "</ul>"
        return html

    def get_tree_node_html(self, t, parent = None):
        html = "<li>"
        if hasattr(t, "content"):
            title = t.content.title
        else:
            title = t.title
        # html += '<a href="%s">%i: %s</a>' % (t.key().name(), 0 if not parent else parent.get_child_order(t.key()), title)      
        html += '<a href="%s">%s</a>' % (t.key().name(), title)  
        if hasattr(t, "children"):
            children = t.children
            if children:
                html += "<ul>"
                for s in children:
                    html += self.get_tree_node_html(s, t)
                html += "</ul>"
        html += "</li>"
        return html

    @user_util.developer_only
    def get(self):
        # t = models.Topic.all().filter("title = ", "Algebra").get()
        # title = t.topic_parent.topic_parent.title
        # logging.info(title)
        # self.load_demo()
        # return
        # self.load_videos()
        # return
        self.hide_topics()
        return
        
        
        root = Topic.get_by_readable_id("root").make_tree()
        # root = models.Topic.get(db.Key.from_path("Topic", "root", "Topic", "math")).make_tree()
        
        '''
        videos = Video.get_videos_with_no_topic()
        template_values = {
            'tree': len(videos) 
            }
        '''

        
        template_values = {
            'tree': self.get_tree_html(root) 
            }

        
        self.render_jinja2_template('edittaxonomy.html', template_values)
        return

    def hide_topics(self):
        from topics_list import topics_list

        root = Topic.get_by_readable_id("root")
        topics = Topic.all().ancestor(root).fetch(10000)
        for topic in topics:
            if topic.title not in topics_list:
                topic.hide = True
                topic.put()
            else:
                topic.hide = False
                topic.put()


    def load_videos(self):
        root = Topic.get_by_readable_id("root")
                        
        title = self.request.get('title', None)
        if title is None:
            playlist = Playlist.all().order('title').get()
        else:
            playlist = Playlist.all().filter('title = ', title).get()
        
        title = playlist.title
        
        nextplaylist = Playlist.all().filter('title >', title).order('title').get()
        if nextplaylist:
            next_title = nextplaylist.title
            next_url = "/admin/edittaxonomy?title="+urllib.quote(next_title)
        else:
            next_title = "FINISHED"
            next_url = None

        # next_url = None
        playlists = [playlist]
        # playlists = Playlist.all().order('title').fetch(100000)
        for i, p in enumerate(playlists):
            videos = p.get_videos()
            topic = Topic.insert(title = p.title,
                         parent = root,
                         description = p.description,
                         child_keys =  [video.key() for video in videos])            
                                    
            context = {
                'current_item': title,
                'next_item': next_title,
                'next_url': next_url,
            } 

            self.render_jinja2_template('update_datastore.html', context)
            
            

    def load_demo(self):
        root = Topic.insert(title = "The Root of All Knowledge",
                            description = "All concepts fit into the root of all knowledge",
                            readable_id = "root")
        '''
        math = Topic.insert(title = "Mathematics",
                            parent = root,
                            description = "All mathematical concepts go here"
                            )
                

        arithmetic = Topic.insert(  title = "Arithmetic",
                                    parent = math,
                                    description = "Arithmetic keywords"
                                   )

        algebra = Topic.insert( title = "Algebra",
                                parent = math,
                                description = "Algebra keywords"
                                )
        '''


        

