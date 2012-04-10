import layer_cache
from video_models import Video
from url_model import Url
from topic_models import Topic, TopicVersion
from setting_model import Setting

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "video_title_dicts_%s" % (
    version_number or Setting.topic_tree_version()))
def video_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return map(lambda video: {
        "title": video.title,
        "key": str(video.key()),
        "relative_url": "/video/%s" % video.readable_id,
        "id": video.readable_id
    }, [v for v in Video.get_all_live(version=version) if v is not None])

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "url_title_dicts_%s" % (
    version_number or Setting.topic_tree_version()))
def url_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return map(lambda url: {
        "title": url.title,
        "key": str(url.key()),
        "ka_url": url.url,
        "id": url.key().id()
    }, Url.get_all_live(version=version))

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "topic_title_dicts_%s" % (
    version_number or Setting.topic_tree_version()))
def topic_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    topic_list = Topic.get_content_topics(version=version)
    topic_list.extend(Topic.get_super_topics(version=version))

    return map(lambda topic: {
        "title": topic.standalone_title,
        "key": str(topic.key()),
        "relative_url": topic.relative_url,
        "id": topic.id
    },  topic_list)

