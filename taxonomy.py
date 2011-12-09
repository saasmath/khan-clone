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
        if t.__class__.__name__ == "Exercise":
            title = "Exercise: " + t.display_name
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
        # self.hide_topics()
        # self.recreate_topic_list_structure()
        # return
        # version = models.TopicVersion.get_latest_version()
        # version.set_default_version()
        # return
        
        # root = Topic.get_by_id("root").make_tree()
        # root = models.Topic.get(db.Key.from_path("Topic", "root", "Topic", "math")).make_tree()
        
        '''
        videos = Video.get_videos_with_no_topic()
        template_values = {
            'tree': len(videos) 
            }
        '''

        
        template_values = {
            #'tree': self.get_tree_html(root) 
            }

        
        self.render_jinja2_template('edittaxonomy.html', template_values)
        return

    def recursive_copy_topic_list_structure(self, parent, topic_list_part):
        delete_topics = {}
        for topic_dict in topic_list_part:
            logging.info(topic_dict["name"])
            if topic_dict.has_key("playlist"):
                topic = Topic.get_by_title_and_parent(topic_dict["name"], parent)
                if topic:
                    logging.info(topic_dict["name"] + " is already created")
                else:
                    topic = Topic.get_by_title(topic_dict["playlist"])
                    delete_topics[topic.key()] = topic
                    logging.info("copying %s to parent %s" % (topic_dict["name"], parent.title))
                    topic.copy(title = topic_dict["name"], parent = parent, standalone_title = topic.title)
            else:
                topic = Topic.get_by_title_and_parent(topic_dict["name"], parent)
                if topic:
                    logging.info(topic_dict["name"] + " is already created")
                else:
                    logging.info("adding %s to parent %s" % (topic_dict["name"], parent.title))
                    topic = Topic.insert(title = topic_dict["name"],
                                         parent = parent
                                         )

            if topic_dict.has_key("items"):
                delete_topics.update(self.recursive_copy_topic_list_structure(topic, topic_dict["items"]))

        return delete_topics       

    def recreate_topic_list_structure(self):
        import topics_list

        root = Topic.get_by_id("root")
        delete_topics = self.recursive_copy_topic_list_structure(root, topics_list.PLAYLIST_STRUCTURE)
        for topic in delete_topics.values():
            topic.delete_tree()

    def hide_topics(self):
        from topics_list import topics_list

        root = Topic.get_by_id("root")
        topics = Topic.all().ancestor(root).fetch(10000)
        for topic in topics:
            if topic.title not in topics_list:
                topic.hide = True
                topic.put()
            else:
                topic.hide = False
                topic.put()


    def load_videos(self):
        root = Topic.get_by_id("root")
                        
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
            exercises = p.get_exercises()
            videos.extend(p.get_exercises())
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
                            id = "root")
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


        

