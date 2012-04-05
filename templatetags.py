import math

from jinja2.utils import escape

from api import jsonify as apijsonify
from templatefilters import slugify
import models
import shared_jinja
import layer_cache
from models import Exercise
import util


def user_info(user_data):
    context = {"user_data": user_data}
    return shared_jinja.get().render_template("user_info_only.html", **context)

def column_major_sorted_videos(topic, num_cols=3, column_width=300, gutter=20, font_size=12):
    content = topic.content
    items_in_column = len(content) / num_cols
    remainder = len(content) % num_cols
    link_height = font_size * 1.5
    # Calculate the column indexes (tops of columns). Since video lists won't divide evenly, distribute
    # the remainder to the left-most columns first, and correctly increment the indices for remaining columns
    column_indices = [(items_in_column * multiplier + (multiplier if multiplier <= remainder else remainder)) for multiplier in range(1, num_cols + 1)]

    template_values = {
        "topic": topic,
        "content": content,
        "column_width": column_width,
        "column_indices": column_indices,
        "link_height": link_height,
        "list_height": column_indices[0] * link_height,
    }

    return shared_jinja.get().render_template("column_major_order_videos.html", **template_values)

def exercise_message(exercise, user_exercise_graph, sees_graph=False,
        review_mode=False):
    """Render UserExercise html for APIActionResults["exercise_message_html"] listener in khan-exercise.js.

    This is called **each time** a problem is either attempted or a hint is called (via /api/v1.py)
    returns nothing unless a user is struggling, proficient, etc. then it returns the appropriat template

    See Also: APIActionResults

    sees_graph is part of an ab_test to see if a small graph will help
    """

    # TODO(david): Should we show a message if the user gets a problem wrong
    #     after proficiency, to explain that this exercise needs to be reviewed?

    exercise_states = user_exercise_graph.states(exercise.name)

    if review_mode and user_exercise_graph.has_completed_review():
        filename = 'exercise_message_review_finished.html'

    elif (exercise_states['proficient'] and not exercise_states['reviewing'] and
            not review_mode):
        if sees_graph:
            filename = 'exercise_message_proficient_withgraph.html'
        else:
            filename = 'exercise_message_proficient.html'

    elif exercise_states['struggling']:
        filename = 'exercise_message_struggling.html'
        suggested_prereqs = []
        if exercise.prerequisites:
            proficient_exercises = user_exercise_graph.proficient_exercise_names()
            for prereq in exercise.prerequisites:
                if prereq not in proficient_exercises:
                    suggested_prereqs.append({
                          'ka_url': Exercise.get_relative_url(prereq),
                          'display_name': Exercise.to_display_name(prereq),
                          })
        exercise_states['suggested_prereqs'] = apijsonify.jsonify(
                suggested_prereqs)

    else:
        return None

    return shared_jinja.get().render_template(filename, **exercise_states)

def user_points(user_data):
    if user_data:
        points = user_data.points
    else:
        points = 0

    return {"points": points}

def streak_bar(user_exercise_dict):
    progress = user_exercise_dict["progress"]

    bar_max_width = 228
    bar_width = min(1.0, progress) * bar_max_width

    levels = []
    if user_exercise_dict["summative"]:
        c_levels = user_exercise_dict["num_milestones"]
        level_offset = bar_max_width / float(c_levels)
        for ix in range(c_levels - 1):
            levels.append(math.ceil((ix + 1) * level_offset) + 1)

    template_values = {
        "is_suggested": user_exercise_dict["suggested"],
        "is_proficient": user_exercise_dict["proficient"],
        "float_progress": progress,
        "progress": models.UserExercise.to_progress_display(progress),
        "bar_width": bar_width,
        "bar_max_width": bar_max_width,
        "levels": levels
    }

    return shared_jinja.get().render_template("streak_bar.html", **template_values)

@layer_cache.cache_with_key_fxn(lambda browser_id, version_number=None:
    "Templatetags.topic_browser_%s_%s" % (
    browser_id, 
    version_number if version_number else models.Setting.topic_tree_version()))
def topic_browser(browser_id, version_number=None):
    if version_number:
        version = models.TopicVersion.get_by_number(version_number)
    else:
        version = None

    root = models.Topic.get_root(version)
    if not root:
        return ""

    tree = root.make_tree(types = ["Topics"])

    # TODO(tomyedwab): Remove this once the confusion over the old Developmental Math playlists settles down
    if not version:
        version = models.TopicVersion.get_default_version()
    developmental_math = models.Topic(
        id="developmental-math",
        version=version,
        title="Developmental Math",
        standalone_title="Developmental Math"
    )
    developmental_math.children = []
    #[topic for topic in tree.children if topic.id == "math"][0].children.append(developmental_math)

    template_values = {
       'browser_id': browser_id, 'topic_tree': tree 
    }

    return shared_jinja.get().render_template("topic_browser.html", **template_values)

def topic_browser_tree(tree, level=0):
    s = ""
    class_name = "topline"
    for child in tree.children:

        if not child.has_children_of_type(["Topic", "Video", "Url"]):
            continue

        if not child.children or child.id in models.Topic._super_topic_ids:
            # special cases
            if child.id == "new-and-noteworthy":
                continue
            elif child.standalone_title == "California Standards Test: Algebra I" and child.id != "algebra-i":
                child.id = "algebra-i"
            elif child.standalone_title == "California Standards Test: Geometry" and child.id != "geometry-2":
                child.id = "geometry-2"

            # show leaf node as a link
            href = "#%s" % escape(slugify(child.id))

            if level == 0:
                s += "<li class='solo'><a href='%s' data-tag='TopicBrowser' class='menulink'>%s</a></li>" % (href, escape(child.title))
            else:
                s += "<li class='%s'><a href='%s' data-tag='TopicBrowser'>%s</a></li>" % (class_name, href, escape(child.title))

        else:
            if level > 0:
                class_name += " sub"

            s += "<li class='%s'>%s <ul>%s</ul></li>" % (class_name, escape(child.title), topic_browser_tree(child, level=level + 1))

        class_name = ""

    return s

def topic_browser_get_topics(tree, level=0, show_topic_pages=False):
    """ Return a two-level tree of topics that we use to build the
        topic browser in the page header. """

    item_list = []
    idx = 0
    needs_divider = False

    for child in tree.children:

        if not child.has_children_of_type(["Topic", "Video", "Url"]):
            continue

        if not child.children or child.id in models.Topic._super_topic_ids:
            # special cases
            if child.id == "new-and-noteworthy":
                continue
            elif child.standalone_title == "California Standards Test: Algebra I" and child.id != "algebra-i":
                child.id = "algebra-i"
            elif child.standalone_title == "California Standards Test: Geometry" and child.id != "geometry-2":
                child.id = "geometry-2"

            # Show leaf node as a link
            item_list.append({
                "level": level,
                "href": child.topic_page_url if show_topic_pages else child.relative_url,
                "title": child.title,
                "has_divider": needs_divider
            })

            needs_divider = False

        elif level == 0:

            # First level gets a popup menu for children
            child_list = topic_browser_get_topics(child, level=level + 1, show_topic_pages=show_topic_pages)

            item_list.append({
                "level": level,
                "href": None,
                "title": child.title,
                "children": child_list
            })

        else:

            # Second level has children embedded into the list
            item_list.append({
                "level": level,
                "href": None,
                "has_children": True,
                "has_divider": True,
                "title": child.title
            })

            item_list += topic_browser_get_topics(child, level=level + 1, show_topic_pages=show_topic_pages)

            needs_divider = True

        idx += 1

    return item_list

@layer_cache.cache_with_key_fxn(lambda version_number=None, show_topic_pages=False:
    "Templatetags.topic_browser_data_%s_%s_v1" % (
    version_number if version_number else models.Setting.topic_tree_version(),
    "ST" if show_topic_pages else "HT"
    ))
def topic_browser_data(version_number=None, show_topic_pages=False):
    """ Returns the JSON data necessary to render the topic browser embedded
        in the page header on the client. """

    if version_number:
        version = models.TopicVersion.get_by_number(version_number)
    else:
        version = None

    root = models.Topic.get_root(version)
    if not root:
        return ""

    tree = root.make_tree(types = ["Topics"])
    topics_list = topic_browser_get_topics(tree, show_topic_pages=show_topic_pages)

    return apijsonify.jsonify(topics_list)

def video_name_and_progress(video):
    return "<span class='vid-progress v%d'>%s</span>" % (video.key().id(), escape(video.title.encode('utf-8', 'ignore')))

def jsonify(obj, camel_cased):
    return apijsonify.jsonify(obj, camel_cased=camel_cased)

def to_secure_url(url):
    """ Returns the appropriate https server URL for a url
    somewhere on Khan Academy. Note - this is not intended for links to
    external sites.

    This abstracts away some of the difficulties and limitations of https
    in the current environment.
    
    """
    
    return util.secure_url(url)

def to_insecure_url(url):
    """ Returns the appropriate http server URL for a url
    somewhere on Khan Academy. Note - this is not intended for links to
    external sites.

    """
    
    return util.insecure_url(url)
