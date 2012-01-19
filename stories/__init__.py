import os
import yaml

import request_handler

class ViewStories(request_handler.RequestHandler):
    def get(self):

        stories = []

        for filename in os.listdir("stories/content"):
            if filename.endswith(".yaml"):

                f = open("stories/content/%s" % filename, "r")
                story = None

                if f:
                    try:
                        contents = f.read()
                        story = yaml.load(contents)
                    finally:
                        f.close()

                if story:
                    story["name"] = filename[:-len(".yaml")]
                    stories.append(story)

        self.render_jinja2_template('stories/stories.html', {
            "stories": stories
        })
