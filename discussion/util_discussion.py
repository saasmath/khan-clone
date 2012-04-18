from google.appengine.api import users

from user_models import UserData
from api.decorators import pickle, unpickle, compress, decompress, base64_encode, base64_decode, protobuf_encode, protobuf_decode
import request_cache
import layer_cache
import discussion_models

def is_honeypot_empty(request):
    return not request.get("honey_input") and not request.get("honey_textarea")

def feedback_query(target_key):
    query = discussion_models.Feedback.all()
    query.filter("targets =", target_key)
    query.order('-date')
    return query

@request_cache.cache_with_key_fxn(discussion_models.Feedback.cache_key_for_video)
@protobuf_decode
@layer_cache.cache_with_key_fxn(discussion_models.Feedback.cache_key_for_video,
                                layer=layer_cache.Layers.Datastore)
@protobuf_encode
def get_feedback_for_video(video):
    return feedback_query(video.key()).fetch(1000)

@request_cache.cache_with_key_fxn(lambda v, ud: str(v) + str(ud))
def get_feedback_for_video_by_user(video_key, user_data_key):
    return feedback_query(video_key).ancestor(user_data_key).fetch(20)

def get_feedback_by_type_for_video(video, feedback_type, user_data=None):
    feedback = [f for f in get_feedback_for_video(video) if feedback_type in f.types]
    feedback_dict = dict([(f.key(), f) for f in feedback])

    user_feedback = []
    if user_data:
        user_feedback = get_feedback_for_video_by_user(video.key(), user_data.key())
    user_feedback_dict = dict([(f.key(), f) for f in user_feedback if feedback_type in f.types])

    feedback_dict.update(user_feedback_dict)
    feedback = feedback_dict.values()

    # Filter out all deleted or flagged feedback (uses hellban technique)
    feedback = filter(lambda f: f.is_visible_to(user_data), feedback)

    return sorted(feedback, key=lambda s: s.date, reverse=True)
