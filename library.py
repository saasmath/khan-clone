import layer_cache
from models import Setting, Topic, TopicVersion
import request_handler
import shared_jinja
import time
import math
import user_util

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

def flatten_tree(tree, parent_topics=[]):
    homepage_topics=[]
    tree.content = []
    tree.subtopics = []

    tree.depth = len(parent_topics)

    if parent_topics:
        if tree.depth == 1 and len(parent_topics[0].subtopics) > 1:
            tree.homepage_title = parent_topics[0].standalone_title + ": " + tree.title
        else:
            tree.homepage_title = tree.title
    else:
        tree.homepage_title = tree.standalone_title

    child_parent_topics = parent_topics[:]

    if tree.id in Topic._super_topic_ids:
        tree.is_super = True
        child_parent_topics.append(tree)
    elif parent_topics:
        child_parent_topics.append(tree)

    for child in tree.children:
        if child.key().kind() == "Topic":
            if child.has_children_of_type(["Topic", "Video", "Url"]):
                tree.subtopics.append(child)
        else:
            tree.content.append(child)

    del tree.children

    if tree.content:
        tree.height = math.ceil(len(tree.content)/3.0) * 18

    if hasattr(tree, "is_super") or (not parent_topics and tree.content):
        homepage_topics.append(tree)

    for subtopic in tree.subtopics:
        homepage_topics += flatten_tree(subtopic, child_parent_topics)

    return homepage_topics

def add_next_topic(topics, next_topic=None):
    topic_prev = None
    for i, topic in enumerate(topics):
        if topic.subtopics:
            topic.next = topic.subtopics[0]
            topic.next_is_subtopic = True
            for subtopic in topic.subtopics:
                add_next_topic(topic.subtopics, next_topic=topics[i+1])
        else:
            if i+1 == len(topics):
                topic.next = next_topic
            else:
                if next_topic:
                    topic.next_is_subtopic = True
                topic.next = topics[i+1]


# A number to increment if the layout of the page, as expected by the client
# side JS changes, and the JS is changed to update it. This version is
# independent of topic content version, and is to do with code versions
_layout_version = 1


@layer_cache.cache_with_key_fxn(
        lambda ajax=False, version_number=None:
        "library_content_by_topic_%s_v%s.%s" % (
        "ajax" if ajax else "inline",
        version_number if version_number else Setting.topic_tree_version(),
        _layout_version),
        layer=layer_cache.Layers.Memcache
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

    # TODO(tomyedwab): Remove this once the confusion over the old Developmental Math playlists settles down
    developmental_math = Topic(
        id="developmental-math",
        version=version,
        title="Developmental Math",
        standalone_title="Developmental Math",
        description="The Developmental Math playlist has been reorganized. The videos which used to be in the Developmental Math playlist can now be found under <a href=\"#algebra\">Algebra</a>."
    )
    developmental_math.is_super = True
    developmental_math.subtopics = []
    developmental_math.homepage_title = "Developmental Math"
    topics.append(developmental_math)

    topics.sort(key = lambda topic: topic.standalone_title)

    # special case the duplicate topics for now, eventually we need to either make use of multiple parent functionality (with a hack for a different title), or just wait until we rework homepage
    topics = [topic for topic in topics 
              if not topic.id == "new-and-noteworthy" and not
              (topic.standalone_title == "California Standards Test: Geometry" 
              and not topic.id == "geometry-2")] 

    # print_topics(topics)

    add_next_topic(topics)

    template_values = {
        'topics': topics,
        'ajax' : ajax,
        'version_date': str(version.made_default_on),
        'version_id': version.number
    }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    return html

@layer_cache.cache_with_key_fxn(
        lambda topic_id, version_number=None: 
        "library_topic_page_%s_v%s" % (
        topic_id,
        version_number if version_number else Setting.topic_tree_version()),
        layer=layer_cache.Layers.Memcache
        )
def library_topic_html(topic_id, version_number=None):
    """" Returns the HTML for the topics on a topic page, including
    the video list.
    """

    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = TopicVersion.get_default_version()

    root_topic = Topic.get_by_id(topic_id, version=version)
    tree = root_topic.make_tree(types=["Topics", "Video", "Url"])
    topics = flatten_tree(tree)

    template_values = {
        'topics': topics,
        'root_topic': root_topic,
        'ajax': False,
        'version_date': str(version.made_default_on),
        'version_id': version.number
    }

    if root_topic.has_content() or root_topic.id in Topic._super_topic_ids:
        html = shared_jinja.get().render_template("library_content_template.html", **template_values)
    else:
        html = shared_jinja.get().render_template("library_condensed_template.html", **template_values)

    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    @user_util.open_access
    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    @user_util.open_access
    def get(self, from_task_queue = False):
        library_content_html(ajax=True, version_number=None, bust_cache=True)
        library_content_html(ajax=False, version_number=None, bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

