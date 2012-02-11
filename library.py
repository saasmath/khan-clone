import layer_cache
from models import Setting, Topic, TopicVersion
import request_handler
import shared_jinja
import time

def flatten_tree(tree, topics_dict, ancestors=None, depth=0, show=False):
    return_topics = []
    
    if tree.id in topics_dict:
        topic = topics_dict[tree.id]
        topic.ancestors = ancestors
        topic.depth = depth
        if depth > 0:
            topic.breadcrumb_title = ""
            if ancestors:
                topic.breadcrumb_title = ancestors[0].title + " : "
            topic.breadcrumb_title += topic.title

        depth += 1
        return_topics.append(topic)
        show = True 

    if ancestors is None:
        ancestors = []

    ancestors = ancestors[:]

    if tree.id in topics_dict or show:
        ancestors.append(tree)

    for child in tree.children:
        return_topics = return_topics + flatten_tree(child, topics_dict, ancestors, depth, show)
    
    return return_topics

@layer_cache.cache_with_key_fxn(
        lambda ajax=False, version_number=None: 
        "library_content_by_topic_%s_v%s" % (
        "ajax" if ajax else "inline", 
        version_number if version_number else Setting.topic_tree_version())
        )
def library_content_html(ajax=False, version_number=None, bust_cache=True):
    """" Returns the HTML for the structure of the topics as they will be
    populated ont he homepage. Does not actually contain the list of video
    names as those are filled in later asynchronously via the cache.
    """
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = TopicVersion.get_default_version()

    topics = Topic.get_filled_content_topics(types = ["Video", "Url"], version=version)
    topics_dict = dict((t.id, t) for t in topics)

    # add the super topics which are not also content topics
    super_topics = dict((t.id, t) for t in Topic.get_super_topics() 
                        if t.id not in topics_dict)
    
    for id, topic in super_topics.iteritems():
        topic.children = []

    topics_dict.update(super_topics)

    tree = Topic.get_root(version).make_tree(types = ["Topics"])
    topics = flatten_tree(tree, topics_dict)

    # special case the duplicate topics for now, eventually we need to either make use of multiple parent functionality (with a hack for a different title), or just wait until we rework homepage
    topics = [topic for topic in topics 
              if not 
              (topic.standalone_title == "California Standards Test: Algebra I" 
              and not topic.id == "algebra-i") and not 
              (topic.standalone_title == "California Standards Test: Geometry" 
              and not topic.id == "geometry-2")] 

    topic_prev = None
    for topic in topics:
        if topic_prev:
            topic_prev.next = topic
        topic_prev = topic

    timestamp = time.time()
    template_values = {
        'topics': topics,
        'ajax' : ajax,
        # convert timestamp to a nice integer for the JS
        'timestamp': int(round(timestamp * 1000)),
        'version_date': str(version.made_default_on),
        'version_id': version.number
    }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    def get(self, from_task_queue = False):
        library_content_html(ajax=True, version_number=None, bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

