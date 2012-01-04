import layer_cache
from models import Video, Topic, Setting, TopicVersion

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "video_title_dicts_%s" % (
    version_number if version_number else Setting.topic_tree_version()))
def video_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return map(lambda video: {
        "title": video.title,
        "key": str(video.key()),
        "ka_url": "/video/%s" % video.readable_id,
        "id": video.readable_id
    }, Video.get_all_live(version=version))

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "topic_title_dicts_%s" % (
    version_number if version_number else Setting.topic_tree_version()))
def topic_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return map(lambda topic: {
        "title": topic.title,
        "key": str(topic.key()),
        "ka_url": topic.ka_url,
        "id": topic.id
    },  Topic.get_content_topics(version=version))



