import datetime

from google.appengine.ext import db

#TODO: Pack object_property so that gandalf does not depend on it
import object_property
from gandalf.filters import find_subclass

class Bridge(db.Model):
    name = db.StringProperty(required=True)
    live = db.BooleanProperty(default=True)
    date_started = db.DateTimeProperty(auto_now_add=True)
    
    @property
    def status(self):
        if self.live:
            days_running = (datetime.datetime.now() - self.date_started).days
            
            if days_running < 1:
                return "Active for less than a day"
            else:
                return "Active for %s day%s" % (days_running, ("" if days_running == 1 else "s"))

        else:
            return "Disabled manually"


class Filter(db.Model):
    bridge = db.ReferenceProperty(Bridge, required=True)
    filter_type = db.StringProperty(required=True)
    whitelist = db.BooleanProperty(default=True)
    percentage = db.IntegerProperty(default=100)
    context = object_property.UnvalidatedObjectProperty()

    @property
    def filter_class(self):
        return find_subclass(self.filter_type)

    @property
    def html(self):
        return self.filter_class.render()

    @property
    def proper_name(self):
        return self.filter_class.proper_name()
