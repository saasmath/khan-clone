import request_handler
import user_util
import cgi
import re
import urllib
import logging
import layer_cache
import urllib2
import re
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
        if self.request.get('migrate', False):
            return self.topic_migration()
        if self.request.get('fixdupes', False):
            return self.fix_duplicates()

        version_name = self.request.get('version', 'edit')

        tree_nodes = []

        edit_version = TopicVersion.get_by_id(version_name)

        root = Topic.get_root(edit_version)
        data = root.get_visible_data()
        tree_nodes.append(data)
        
        template_values = {
            'edit_version': jsonify(edit_version),
            'tree_nodes': jsonify(tree_nodes)
            }
 
        self.render_jinja2_template('topics-admin.html', template_values)
        return

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

# temporary function to recreate the root - will remove after deploy
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
    request = urllib2.Request("http://smarthistory.org/khan-home.html")
    try:
        response = urllib2.urlopen(request)
        smart_history = response.read()
        smart_history = re.search(re.compile("<body>(.*)</body>", re.S), smart_history).group(1).decode("utf-8")
        smart_history.replace("script", "")
    except urllib2.URLError, e:
        logging.exception("Failed fetching smarthistory video list")
        smart_history = None
    return smart_history


class ImportSmartHistory(request_handler.RequestHandler):

    def get(self):
        """update the default and edit versions of the topic tree with smarthistory (creates a new default version if there are changes)"""
        default = models.TopicVersion.get_default_version()
        edit = models.TopicVersion.get_edit_version()
        ImportSmartHistory.importIntoVersion(default)
        ImportSmartHistory.importIntoVersion(edit)
    
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
                                 description="Spontaneous conversations about works of art where the speakers are not afraid to disagree with each other or art history orthodoxy. Videos are made by <b>Dr. Beth Harris and Dr. Steven Zucker along with other contributors.</b>")
        
        urls = topic.get_urls()
        href_to_key_dict = dict((url.url, url.key()) for url in urls)
        hrefs = [url.url for url in urls]
        content = getSmartHistoryContent()
        child_keys = []
        i = 0
        for link in re.finditer(re.compile('<a.*href="(.*?)"><span.*?>(.*)</span></a>', re.M), content):
            href = link.group(1)
            title = link.group(2)
            if href not in hrefs:
                logging.info("adding %i %s %s to art-history" % (i, href, title))
                url = Url(url=href,
                          title=title,
                          id=id)
                url.put()
                child_keys.append(url.key())
                i += 1
            else:
                child_keys.append(href_to_key_dict[href])

        logging.info("updating child_keys")
        if topic.child_keys != child_keys:
            if version.default:
                logging.info("creating new default version")
                new_version = version.copy_version()
                new_version.description = "SmartHistory Update"
                new_version.put()
                new_topic = Topic.get_by_id("art-history", new_version)
                new_topic.update(child_keys=child_keys)
                new_version.set_default_version()
            else:
                topic.update(child_keys=child_keys)
            logging.info("finished updating version number %i" % version.number)
        else:
            logging.info("nothing changed")

