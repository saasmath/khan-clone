"""These are database entities that are not currently used.

They should all be deleted.  Some are still (wrongly) referenced
elsewhere in the code, so we can't quite delete them yet.
"""

# I haven't bothered to fix up imports for these since they're going
# away.

import urllib

from google.appengine.api import memcache
from google.appengine.ext import db

from app import App
from search import Searchable
from templatefilters import slugify
from topics_list import all_topics_list
import layer_cache
import object_property
import util

from setting_model import Setting
from video_models import Video


class Playlist(Searchable, db.Model):

    youtube_id = db.StringProperty()
    url = db.StringProperty()
    title = db.StringProperty()
    description = db.TextProperty()
    readable_id = db.StringProperty() #human readable, but unique id that can be used in URLS
    tags = db.StringListProperty()
    INDEX_ONLY = ['title', 'description']
    INDEX_TITLE_FROM_PROP = 'title'
    INDEX_USES_MULTI_ENTITIES = False

    _serialize_blacklist = ["readable_id"]

    @property
    def ka_url(self):
        return util.absolute_url(self.relative_url)

    @property
    def relative_url(self):
        return '#%s' % urllib.quote(slugify(self.title.lower()))

    @staticmethod
    def get_for_all_topics():
        return filter(lambda playlist: playlist.title in all_topics_list,
                Playlist.all().fetch(1000))

    def get_videos(self):
        video_query = Video.all()
        video_query.filter('playlists = ', self.title)
        video_key_dict = Video.get_dict(video_query, lambda video: video.key())

        video_playlist_query = VideoPlaylist.all()
        video_playlist_query.filter('playlist =', self)
        video_playlist_query.filter('live_association =', True)
        video_playlist_key_dict = VideoPlaylist.get_key_dict(video_playlist_query)
        if not video_playlist_key_dict.has_key(self.key()):
            return []
        video_playlists = sorted(video_playlist_key_dict[self.key()].values(), key=lambda video_playlist: video_playlist.video_position)

        videos = []
        for video_playlist in video_playlists:
            video = video_key_dict[VideoPlaylist.video.get_value_for_datastore(video_playlist)]
            video.position = video_playlist.video_position
            videos.append(video)

        return videos

    def get_video_count(self):
        video_playlist_query = VideoPlaylist.all()
        video_playlist_query.filter('playlist =', self)
        video_playlist_query.filter('live_association =', True)
        return video_playlist_query.count()


class UserPlaylist(db.Model):
    user = db.UserProperty()
    playlist = db.ReferenceProperty(Playlist)
    seconds_watched = db.IntegerProperty(default=0)
    last_watched = db.DateTimeProperty(auto_now_add=True)
    title = db.StringProperty(indexed=False)

    @staticmethod
    def get_for_user_data(user_data):
        query = UserPlaylist.all()
        query.filter('user =', user_data.user)
        return query

    @staticmethod
    def get_key_name(playlist, user_data):
        return user_data.key_email + ":" + playlist.youtube_id

    @staticmethod
    def get_for_playlist_and_user_data(playlist, user_data, insert_if_missing=False):
        if not user_data:
            return None

        key = UserPlaylist.get_key_name(playlist, user_data)

        if insert_if_missing:
            return UserPlaylist.get_or_insert(
                        key_name=key,
                        user=user_data.user,
                        playlist=playlist)
        else:
            return UserPlaylist.get_by_key_name(key)


# Represents a matching between a playlist and a video
# Allows us to keep track of which videos are in a playlist and
# which playlists a video belongs to (not 1-to-1 mapping)
class VideoPlaylist(db.Model):

    playlist = db.ReferenceProperty(Playlist)
    video = db.ReferenceProperty(Video)
    video_position = db.IntegerProperty()

    # Lets us enable/disable video playlist relationships in bulk without removing the entry
    live_association = db.BooleanProperty(default=False)
    last_live_association_generation = db.IntegerProperty(default=0)

    _VIDEO_PLAYLIST_KEY_FORMAT = "VideoPlaylist_Videos_for_Playlist_%s"
    _PLAYLIST_VIDEO_KEY_FORMAT = "VideoPlaylist_Playlists_for_Video_%s"

    @staticmethod
    def get_namespace():
        return "%s_%s" % (App.version, Setting.topic_tree_version())

    @staticmethod
    def get_cached_videos_for_playlist(playlist, limit=500):

        key = VideoPlaylist._VIDEO_PLAYLIST_KEY_FORMAT % playlist.key()
        namespace = VideoPlaylist.get_namespace()

        videos = memcache.get(key, namespace=namespace)

        if not videos:
            query = VideoPlaylist.all()
            query.filter('playlist =', playlist)
            query.filter('live_association = ', True)
            query.order('video_position')
            videos = [video_playlist.video for video_playlist in query.fetch(limit)]

            memcache.set(key, videos, namespace=namespace)

        return videos

    @staticmethod
    def get_cached_playlists_for_video(video, limit=5):

        key = VideoPlaylist._PLAYLIST_VIDEO_KEY_FORMAT % video.key()
        namespace = VideoPlaylist.get_namespace()

        playlists = memcache.get(key, namespace=namespace)

        if playlists is None:
            query = VideoPlaylist.all()
            query.filter('video =', video)
            query.filter('live_association = ', True)
            playlists = [video_playlist.playlist for video_playlist in query.fetch(limit)]

            memcache.set(key, playlists, namespace=namespace)

        return playlists

    @staticmethod
    def get_query_for_playlist_title(playlist_title):
        query = Playlist.all()
        query.filter('title =', playlist_title)
        playlist = query.get()
        query = VideoPlaylist.all()
        query.filter('playlist =', playlist)
        query.filter('live_association = ', True) # need to change this to true once I'm done with all of my hacks
        query.order('video_position')
        return query

    @staticmethod
    def get_key_dict(query):
        video_playlist_key_dict = {}
        for video_playlist in query.fetch(10000):
            playlist_key = VideoPlaylist.playlist.get_value_for_datastore(video_playlist)

            if not video_playlist_key_dict.has_key(playlist_key):
                video_playlist_key_dict[playlist_key] = {}

            video_playlist_key_dict[playlist_key][VideoPlaylist.video.get_value_for_datastore(video_playlist)] = video_playlist

        return video_playlist_key_dict

