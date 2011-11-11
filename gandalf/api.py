from google.appengine.ext.webapp import RequestHandler
from google.appengine.ext import db

from gandalf.jsonify import jsonify
from gandalf.config import can_control_gandalf
from gandalf.models import Bridge, Filter
from gandalf.filters import BridgeFilter, find_subclass


class Bridges(RequestHandler): 
    def get(self):

        if not can_control_gandalf():
            return

        bridges = Bridge.all().fetch(500)


        context = {
            "bridges": bridges,
        }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))


class Filters(RequestHandler):
    def get(self):

        if not can_control_gandalf():
            return

        bridge_name = self.request.get('bridge_name')
        bridge = Bridge.all().filter('name =', bridge_name)[0]

        try:
            filters = bridge.filter_set.order('-__key__').fetch(500)
        except IndexError:
            filters = None

        filter_types = [{
            'proper_name': subclass.proper_name(),
            'name': subclass.name,
        } for subclass in BridgeFilter.__subclasses__()]

        context = { 
            'filters': filters,
            'filter_types': filter_types,
            'bridge_name': bridge.name,
            'bridge_live': bridge.live,
        }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))

class UpdateBridge(RequestHandler):
    def post(self):

        if not can_control_gandalf():
            return

        action = self.request.get('action')
        bridge_name = self.request.get('bridge_name')

        if action == 'new':

            # Check that there are no existing bridges with that bridge_name
            try:
                Bridge.all().filter('name =', bridge_name)[0]

                context = { 
                    'error': "There is already a bridge with that name",
                }

                self.response.headers["Content-Type"] = "application/json"
                self.response.out.write(jsonify(context))

                return 

            except IndexError:
                pass
                
            bridge = Bridge(name=bridge_name)
            bridge.put()

        elif action == 'disable':

            live = self.request.get('live')

            bridge = Bridge.all().filter('name =', bridge_name)[0]

            bridge.live = live == 'true'

            bridge.put()

        context = { 
            "success": True,
        }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))


class UpdateFilter(RequestHandler):
    def post(self):

        if not can_control_gandalf():
            return

        action = self.request.get('action')

        if action == "new":

            filter_type = self.request.get('filter_type')
            
            bridge_name = self.request.get('bridge_name')
            bridge = Bridge.all().filter('name =', bridge_name)[0]

            context = find_subclass(filter_type).initial_context()

            filter = Filter(bridge=bridge, filter_type=filter_type, context=context)


            filter.put()

        else:

            filter_key = self.request.get('filter_key')
            filter = Filter.get(filter_key)

            if action == "delete":

                filter.delete()

            elif action == "save":

                whitelist = self.request.get('whitelist')

                try:
                    percentage = int(self.request.get('percentage'))
                except ValueError:
                    percentage = 100

                if percentage < 0 or percentage > 100:
                    return

                filter = Filter.get(filter_key)
               
                filter.whitelist = whitelist == "true"
                filter.percentage = percentage

                for key in filter.context:
                    value = self.request.get(key)
                    if value is not None:
                        filter.context[key] = value

                filter.put()

        context = { 
            "success": True,
        }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))
