import layer_cache
from models import Video, Topic
from templatefilters import slugify

CACHE_EXPIRATION_SECONDS = 60 * 60 * 24 * 3 # Expires after three days

@layer_cache.cache(expiration=CACHE_EXPIRATION_SECONDS)
def video_title_dicts():
    return map(lambda video: {
        "title": video.title,
        "key": str(video.key()),
        "ka_url": "/video/%s" % video.readable_id
    }, Video.get_all_live())

@layer_cache.cache(expiration=CACHE_EXPIRATION_SECONDS)
def topic_title_dicts():
    return map(lambda topic: {
        "title": topic.title,
        "key": str(topic.key()),
        "ka_url": topic.ka_url
    },  Topic.get_content_topics())


