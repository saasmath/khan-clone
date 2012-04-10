import request_handler
import user_util
import cgi
import re
import urllib
import logging
import layer_cache
import urllib2
from knowledgemap import layout
from youtube_sync import youtube_get_video_data_dict

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import zlib
import cPickle as pickle

from api.auth.xsrf import ensure_xsrf_cookie
from google.appengine.ext import deferred



from api.jsonify import jsonify
from api.auth.decorators import developer_required

from google.appengine.ext import db


import models
from models import Topic, TopicVersion, Video, Url
from models import Playlist
        
class EditContent(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    @user_util.developer_only
    def get(self):

        version_name = self.request.get('version', 'edit')

        edit_version = TopicVersion.get_by_id(version_name)
        if edit_version is None:
            default_version = TopicVersion.get_default_version()
            if default_version is None:
                # Assuming this is dev, there is an empty datastore and we need an import
                edit_version = TopicVersion.create_new_version()
                edit_version.edit = True
                edit_version.put()
                create_root(edit_version)
            else:
                raise Exception("Wait for setting default version to finish making an edit version.")

        if self.request.get('autoupdate', False):
            self.render_jinja2_template('autoupdate_in_progress.html', {"edit_version": edit_version})
            return
        if self.request.get('autoupdate_begin', False):
            return self.topic_update_from_live(edit_version)
        if self.request.get('migrate', False):
            return self.topic_migration()
        if self.request.get('fixdupes', False):
            return self.fix_duplicates()

        root = Topic.get_root(edit_version)
        data = root.get_visible_data()
        tree_nodes = [data]
        
        template_values = {
            'edit_version': jsonify(edit_version),
            'tree_nodes': jsonify(tree_nodes)
            }
 
        self.render_jinja2_template('topics-admin.html', template_values)
        return

    def topic_update_from_live(self, edit_version):
        layout.update_from_live(edit_version)
        request = urllib2.Request("http://www.khanacademy.org/api/v1/topictree")
        try:
            opener = urllib2.build_opener()
            f = opener.open(request)
            topictree = json.load(f)

            logging.info("calling /_ah/queue/deferred_import")

            # importing the full topic tree can be too large so pickling and compressing
            deferred.defer(models.topictree_import_task, "edit", "root", True,
                        zlib.compress(pickle.dumps(topictree)),
                        _queue="import-queue",
                        _url="/_ah/queue/deferred_import")

        except urllib2.URLError, e:
            logging.exception("Failed to fetch content from khanacademy.org")

    def topic_migration(self):
        logging.info("deleting all existing topics")
        db.delete(models.Topic.all())
        db.delete(models.TopicVersion.all())
        db.delete(models.Url.all())

        version = models.TopicVersion.all().filter("edit =", True).get()
        if version is None:
            version = models.TopicVersion.create_new_version()
            version.edit = True
            version.put()
        logging.info("starting migration")
        create_root(version)
        logging.info("created root")
        logging.info("loading playlists")
        deferred.defer(load_videos, version)
        print "migration started... progress can be monitored in the logs"

    def fix_duplicates(self):
        dry_run = self.request.get('dry_run', False)
        video_list = [v for v in models.Video.all()]
        video_dict = dict()

        version = models.TopicVersion.get_by_id("edit")

        videos_to_update = []
        
        for video in video_list:
            if not video.readable_id in video_dict:
                video_dict[video.readable_id] = []
            video_dict[video.readable_id].append(video)

        video_idx = 0
        print "IDX,Canon,DUP,Key,ID,YTID,Title,Topics"

        for readable_id, videos in video_dict.iteritems():
            if len(videos) > 1:
                canonical_key_id = 0
                canonical_readable_id = None
                for video in videos:
                    if models.Topic.all().filter("version = ", version).filter("child_keys =", video.key()).get():
                        canonical_key_id = video.key().id()
                    if not canonical_readable_id or len(video.readable_id) < len(canonical_readable_id):
                        canonical_readable_id = video.readable_id
                
                def print_video(video, is_canonical, dup_idx):
                    canon_str = "CANONICAL" if is_canonical else "DUPLICATE"
                    topic_strings = "|".join([topic.id for topic in models.Topic.all().filter("version = ", version).filter("child_keys =", video.key()).run()])
                    print "%d,%s,%d,%s,%s,%s,%s,%s" % (video_idx, canon_str, dup_idx, str(video.key()), video.readable_id, video.youtube_id, video.title, topic_strings)

                for video in videos:
                    if video.key().id() == canonical_key_id:
                        if video.readable_id != canonical_readable_id:
                            video.readable_id = canonical_readable_id
                            videos_to_update.append(video)

                        print_video(video, True, 0)

                dup_idx = 1
                for video in videos:
                    if video.key().id() != canonical_key_id:
                        new_readable_id = canonical_readable_id + "_DUP_" + str(dup_idx)

                        if video.readable_id != new_readable_id:
                            video.readable_id = new_readable_id
                            videos_to_update.append(video)

                        print_video(video, False, dup_idx)

                        dup_idx += 1

                video_idx += 1

        if len(videos_to_update) > 0:
            logging.info("Writing " + str(len(videos_to_update)) + " videos with duplicate IDs")
            if not dry_run:
                db.put(videos_to_update)
            else:
                logging.info("Just kidding! This is a dry run.")
        else:
            logging.info("No videos to update.")

# function to create the root, needed for first import into a dev env
def create_root(version):
    root = Topic.insert(title="The Root of All Knowledge",
            description="All concepts fit into the root of all knowledge",
            id="root",
            version=version)


# temporary function to load videos into the topics - will remove after deploy
def load_videos(version, title=None):
    root = Topic.get_by_id("root", version)
                    
    if title is None:
        playlist = Playlist.all().order('title').get()
    else:
        playlist = Playlist.all().filter('title = ', title).get()
    
    title = playlist.title
    
    nextplaylist = Playlist.all().filter('title >', title).order('title').get()
    if nextplaylist:
        next_title = nextplaylist.title

    playlists = [playlist]
    # playlists = Playlist.all().order('title').fetch(100000)
    for i, p in enumerate(playlists):
        videos = p.get_videos()
        content_keys = [v.key() for v in videos]
        added = 0
        for i, v in enumerate(videos):
            for e in v.related_exercises():
                if e.key() not in content_keys:
                    content_keys.insert(i + added, e.key())
                    added += 1

        topic = Topic.insert(title=p.title,
                     parent=root,
                     description=p.description,
                     tags=p.tags,
                     child_keys=content_keys)
    
    logging.info("loading " + title)
    
    if nextplaylist:
        deferred.defer(load_videos, version, next_title)
    else:
        deferred.defer(hide_topics, version)


# temporary function for marking topics not in topics_list.py as
# hidden - will remove after deploy
def hide_topics(version):
    from topics_list import topics_list
    logging.info("hiding topics")

    root = Topic.get_by_id("root", version)
    topics = Topic.all().ancestor(root).fetch(10000)
    for topic in topics:
        if topic.title not in topics_list:
            topic.hide = True
            topic.put()
        else:
            topic.hide = False
            topic.put()

    logging.info("hid topics")
    deferred.defer(recreate_topic_list_structure)


# temporary function for copying the topic structure in topics_list.py
# will remove after deploy
def recursive_copy_topic_list_structure(parent, topic_list_part):
    delete_topics = {}
    for topic_dict in topic_list_part:
        logging.info(topic_dict["name"])
        if "playlist" in topic_dict:
            topic = Topic.get_by_title_and_parent(topic_dict["name"], parent)
            if topic:
                logging.info(topic_dict["name"] + " is already created")
            else:
                version = TopicVersion.get_edit_version()
                root = Topic.get_root(version)
                topic = Topic.get_by_title_and_parent(topic_dict["playlist"], root)
                if topic:
                    delete_topics[topic.key()] = topic
                    logging.info("copying %s to parent %s" %
                                (topic_dict["name"], parent.title))
                    topic.copy(title=topic_dict["name"], parent=parent,
                               standalone_title=topic.title)
                else:
                    logging.error("Topic not found! %s" % (topic_dict["playlist"]))
        else:
            topic = Topic.get_by_title_and_parent(topic_dict["name"], parent)
            if topic:
                logging.info(topic_dict["name"] + " is already created")
            else:
                logging.info("adding %s to parent %s" %
                             (topic_dict["name"], parent.title))
                topic = Topic.insert(title=topic_dict["name"], parent=parent)

        if "items" in topic_dict:
            delete_topics.update(
                recursive_copy_topic_list_structure(topic,
                                                    topic_dict["items"]))

    return delete_topics


# temporary function for copying the topic structure in topics_list.py ... will remove after deploy
def recreate_topic_list_structure():
    import topics_list
    logging.info("recreating topic_list structure")

    version = TopicVersion.get_edit_version()
    root = Topic.get_by_id("root", version)
    delete_topics = recursive_copy_topic_list_structure(root, topics_list.PLAYLIST_STRUCTURE)
    for topic in delete_topics.values():
        topic.delete_tree()
    deferred.defer(importSmartHistory)


# temporary function to load smarthistory the first time during migration
def importSmartHistory():
    edit = models.TopicVersion.get_edit_version()
    ImportSmartHistory.importIntoVersion(edit)
    edit.set_default_version()
    new_edit = TopicVersion.create_edit_version()

                
# temporary function to remove playlist from the fulltext index...
# will remove after we run it once after it gets deployed
def removePlaylistIndex():
    import search

    items = search.StemmedIndex.all(keys_only=True).filter("parent_kind", "Playlist").fetch(10000)
    db.delete(items)


@layer_cache.cache(layer=layer_cache.Layers.Memcache | layer_cache.Layers.Datastore, expiration=86400)
def getSmartHistoryContent():
    request = urllib2.Request("http://khan.smarthistory.org/youtube-urls-for-khan-academy.html")
    try:
        opener = urllib2.build_opener()
        f = opener.open(request)
        smart_history = json.load(f)
    except urllib2.URLError, e:
        logging.exception("Failed fetching smarthistory video list")
        smart_history = None
    return smart_history

class ImportSmartHistory(request_handler.RequestHandler):

    @user_util.open_access
    def get(self):
        """update the default and edit versions of the topic tree with smarthistory (creates a new default version if there are changes)"""
        default = models.TopicVersion.get_default_version()
        edit = models.TopicVersion.get_edit_version()
        
        logging.info("importing into edit version")
        # if there are any changes to the edit version
        if ImportSmartHistory.importIntoVersion(edit):

            # make a copy of the default version, 
            # update the copy and then mark it default
            logging.info("creating new default version")
            new_version = default.copy_version()
            new_version.title = "SmartHistory Update"
            new_version.put()

            logging.info("importing into new version")
            ImportSmartHistory.importIntoVersion(new_version)
                
            logging.info("setting version default")
            new_version.set_default_version()
            logging.info("done setting version default")

        logging.info("done importing smart history")

                        
    @staticmethod
    def importIntoVersion(version):
        logging.info("comparing to version number %i" % version.number)
        topic = Topic.get_by_id("art-history", version)

        if not topic:
            parent = Topic.get_by_id("humanities---other", version)
            if not parent:
                raise Exception("Could not find the Humanities & Other topic to put art history into")
            topic = Topic.insert(title="Art History",
                                 parent=parent,
                                 id="art-history",
                                 standalone_title="Art History",
                                 description="Spontaneous conversations about works of art where the speakers are not afraid to disagree with each other or art history orthodoxy. Videos are made by Dr. Beth Harris and Dr. Steven Zucker along with other contributors.")
        
        urls = topic.get_urls(include_descendants=True)
        href_to_key_dict = dict((url.url, url.key()) for url in urls)
        
        videos = topic.get_videos(include_descendants=True)
        video_dict = dict((v.youtube_id, v) for v in videos)

        content = getSmartHistoryContent()
        if content is None:
            raise Exception("Aborting import, could not read from smarthistory")

        subtopics = topic.get_child_topics()
        subtopic_dict = dict((t.title, t) for t in subtopics)
        subtopic_child_keys = {}
        
        new_subtopic_keys = []

        child_keys = []
        i = 0
        for link in content:
            href = link["href"]
            title = link["title"]
            parent_title = link["parent"]
            content = link["content"]
            youtube_id = link["youtube_id"] if "youtube_id" in link else None
            extra_properties = {"original_url": href}

            if parent_title not in subtopic_dict:
                subtopic = Topic.insert(title=parent_title,
                                 parent=topic,
                                 standalone_title="Art History: %s" 
                                                  % parent_title,
                                 description="")

                subtopic_dict[parent_title] = subtopic
            else:
                subtopic = subtopic_dict[parent_title]
           
            if subtopic.key() not in new_subtopic_keys:
                new_subtopic_keys.append(subtopic.key())

            if parent_title not in subtopic_child_keys:
                 subtopic_child_keys[parent_title] = []
            
            if youtube_id:
                if youtube_id not in video_dict:
                    # make sure it didn't get imported before, but never put 
                    # into a topic
                    query = models.Video.all()
                    video = query.filter("youtube_id =", youtube_id).get()

                    if video is None:
                        logging.info("adding youtube video %i %s %s %s to %s" % 
                                     (i, youtube_id, href, title, parent_title))
                        
                        video_data = youtube_get_video_data_dict(youtube_id)
                        # use the title from the webpage not from the youtube 
                        # page
                        video = None
                        if video_data:
                            video_data["title"] = title
                            video_data["extra_properties"] = extra_properties
                            video = models.VersionContentChange.add_new_content(
                                                                models.Video,
                                                                version,
                                                                video_data)
                        else:
                            logging.error(("Could not import youtube_id %s " +
                                          "for %s %s") % (youtube_id, href, title))
                            
                            raise Exception(("Could not import youtube_id %s " +
                                            " for %s %s") % (youtube_id, href, 
                                            title))

                else:
                    video = video_dict[youtube_id] 
                    if video.extra_properties != extra_properties:
                        logging.info(("changing extra properties of %i %s %s " +
                                     "from %s to %s") % (i, href, title, 
                                     video.extra_properties, extra_properties))
                        
                        video.extra_properties = extra_properties
                        video.put()
                                    
                if video:
                    subtopic_child_keys[parent_title].append(video.key())

            elif href not in href_to_key_dict:
                logging.info("adding %i %s %s to %s" % 
                             (i, href, title, parent_title))
                
                models.VersionContentChange.add_new_content(
                    models.Url, 
                    version,
                    {"title": title,
                     "url": href
                    },
                    ["title", "url"])

                url = Url(url=href,
                          title=title,
                          id=id)

                url.put()
                subtopic_child_keys[parent_title].append(url.key())

            else:
                subtopic_child_keys[parent_title].append(href_to_key_dict[href])

            i += 1

        logging.info("updating child_keys")
        change = False
        for parent_title, child_keys in subtopic_child_keys.iteritems():
            subtopic = subtopic_dict[parent_title]
            if subtopic.child_keys != subtopic_child_keys[parent_title]:
                change = True
                subtopic.update(child_keys=subtopic_child_keys[parent_title])
        
        if topic.child_keys != new_subtopic_keys:    
            change = True
            topic.update(child_keys=new_subtopic_keys)
        
        if change:
            logging.info("finished updating version number %i" % version.number)
        else:
            logging.info("nothing changed")

        return change
