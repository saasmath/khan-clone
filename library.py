import layer_cache
from models import Setting, Topic, TopicVersion
import request_handler
import shared_jinja
import time
import math

# helpful function to see topic structure from the console.  In the console:
# import library
# library.library_content_html(bust_cache=True)
#
# Within library_content_html: print_topics(topics)
def print_topics(topics):
    for topic in topics:
        print topic.homepage_title
        print topic.depth
        if topic.subtopics:
            print "subtopics:"
            for subtopic in topic.subtopics:
                print subtopic.homepage_title
                if subtopic.subtopics:
                    print "subsubtopics:"
                    for subsubtopic in subtopic.subtopics:
                        print subsubtopic.homepage_title
                    print " "
            print " "
        print " "

def flatten_tree(tree, super_topic=None, sub_topic=None, depth=0):
    homepage_topics=[]
    tree.content = []
    tree.subtopics = []
    
    if super_topic:
        depth += 1

    tree.depth = depth

    if super_topic:
        if depth == 1:
            tree.homepage_title = super_topic.standalone_title + ": " + tree.title
        else:
            tree.homepage_title = tree.title
    else:
        tree.homepage_title = tree.standalone_title

    if tree.id in Topic._super_topic_ids:
        tree.is_super = True
        super_topic = tree

    for child in tree.children:
        if child.key().kind() == "Topic":
            tree.subtopics.append(child)
        else:
            tree.content.append(child)

    del tree.children
    tree.leaf_topics = []

    if tree.content:
        tree.height = math.ceil(len(tree.content)/3.0) * 18

    if hasattr(tree, "is_super") or tree.content or depth:
        if sub_topic:
            sub_topic.leaf_topics.append(tree)
        else:
            homepage_topics.append(tree)

    if super_topic and not hasattr(tree, "is_super") and not sub_topic:
        sub_topic = tree

    for subtopic in tree.subtopics:
        homepage_topics += flatten_tree(subtopic, super_topic, sub_topic, depth)

    return homepage_topics

@layer_cache.cache_with_key_fxn(
        lambda ajax=False, version_number=None: 
        "library_content_by_topic_%s_v%s" % (
        "ajax" if ajax else "inline", 
        version_number if version_number else Setting.topic_tree_version()),
        layer=layer_cache.Layers.Blobstore
        )
def library_content_html(ajax=False, version_number=None):
    """" Returns the HTML for the structure of the topics as they will be
    populated ont he homepage. Does not actually contain the list of video
    names as those are filled in later asynchronously via the cache.
    """
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = TopicVersion.get_default_version()


    tree = Topic.get_root(version).make_tree(types = ["Topics", "Video", "Url"])
    topics = flatten_tree(tree)

    # special case the duplicate topics for now, eventually we need to either make use of multiple parent functionality (with a hack for a different title), or just wait until we rework homepage
    topics = [topic for topic in topics 
              if not 
              (topic.standalone_title == "California Standards Test: Algebra I" 
              and not topic.id == "algebra-i") and not 
              (topic.standalone_title == "California Standards Test: Geometry" 
              and not topic.id == "geometry-2")] 

    # print_topics(topics)

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

