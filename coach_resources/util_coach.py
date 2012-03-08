import request_handler
import util
from models import UserData

class CoachResourcesRequestHandler(request_handler.RequestHandler):
    def render_jinja2_template(self, template_name, template_values):
        template_values['selected_nav_link'] = 'coach'
        request_handler.RequestHandler.render_jinja2_template(self, template_name, template_values)

class ViewCoachResources(CoachResourcesRequestHandler):
    def get(self):
        coach = UserData.current()

        if coach is not None:
            coach_email = coach.email
            is_profile_empty = not coach.has_students()
        else:
            coach_email = None
            is_profile_empty = True

        self.render_jinja2_template('coach_resources/view_resources.html', {
            'selected_id': 'coach-resources',
            'coach_email': coach_email,
            'is_profile_empty': is_profile_empty,
        })

class ViewToolkit(CoachResourcesRequestHandler):
    def get(self, toolkit_section=None):
        
        # make /toolkit use the view_toolkit template
        
        template = 'coach_resources'
        
        if not toolkit_section:
            toolkit_section = 'index'
            
        # TODO(Matt): Error catching for bad URLs    
            
        template += '/toolkit_content/' + toolkit_section + '.html'
        
                
        self.render_jinja2_template(template, {
            'selected_id': 'toolkit',
        })

class ViewBlog(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/schools_blog.html', {
            "selected_id": "schools-blog",
        })

class ViewDemo(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/demo.html', {
            "selected_id": "demo",
        })

class ViewFAQ(CoachResourcesRequestHandler):
    def get(self):
        self.render_jinja2_template('coach_resources/schools-faq.html', {})
