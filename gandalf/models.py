import datetime

from google.appengine.ext import db

#TODO: Pack object_property so that gandalf does not depend on it
import object_property
from gandalf.filters import BridgeFilter

class _GandalfBridge(db.Model):
    date_created = db.DateTimeProperty(auto_now_add=True, indexed=False)
    
    @property
    def status(self):
        days_running = (datetime.datetime.now() - self.date_created).days
        
        if days_running < 1:
            return "Running for less than a day"
        else:
            return "Running for %s day%s" % (days_running, ("" if days_running == 1 else "s"))


class _GandalfFilter(db.Model):
    bridge = db.ReferenceProperty(_GandalfBridge, required=True)
    filter_type = db.StringProperty(required=True, indexed=False)
    whitelist = db.BooleanProperty(default=True, indexed=False)
    percentage = db.IntegerProperty(default=100, indexed=False)
    context = object_property.UnvalidatedObjectProperty(indexed=False)

    @property
    def filter_class(self):
        return BridgeFilter.find_subclass(self.filter_type)

    @property
    def html(self):
        return self.filter_class.render()

    @property
    def proper_name(self):
        return self.filter_class.proper_name()
