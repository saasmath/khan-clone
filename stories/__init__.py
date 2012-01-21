import os
import yaml

from google.appengine.api import mail

from app import App
import request_handler

FROM_EMAIL = "no-reply@khan-academy.appspotmail.com"
TO_EMAIL = "testimonials@khanacademy.org"

class SubmitStory(request_handler.RequestHandler):
    def post(self):
        """ This is a temporary method of sending in users' submitted stories.
        We can obviously turn this into a nicer CRUD interface if stories
        do well and email management is a pain."""

        story = self.request_string("story")
        share_allowed = self.request_bool("share")

        if len(story) == 0:
            return

        subject = "Testimonial story submitted"
        if share_allowed:
            subject += " (sharing with others allowed)"
        else:
            subject += " (sharing with others *NOT* allowed)"

        if not App.is_dev_server:
            mail.send_mail( \
                    sender = FROM_EMAIL, \
                    to = TO_EMAIL, \
                    subject = subject, \
                    body = story)

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
