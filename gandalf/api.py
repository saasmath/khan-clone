from google.appengine.ext.webapp import RequestHandler
from google.appengine.ext import db
from google.appengine.api.datastore_errors import BadValueError

from gandalf.jsonify import jsonify
from gandalf.config import can_control_gandalf
from gandalf.models import _GandalfBridge, _GandalfFilter
from gandalf.filters import BridgeFilter


class Bridges(RequestHandler): 
    def get(self):

        if not can_control_gandalf():
            return

        bridges = _GandalfBridge.all().fetch(900)

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

        if not bridge_name:
            raise Exception("Must include 'bridge_name' parameter")

        try:
            bridge = _GandalfBridge.get_by_key_name(bridge_name)
        except BadValueError:
            raise Exception("Bridge '%s' does not exist" % bridge_name)

        filters = bridge._gandalffilter_set.order('-__key__').fetch(500)

        context = { 
            'filters': filters,
            'filters_is_not_empty': bool(filters),
            'filter_types': BridgeFilter.get_filter_types(),
            'bridge': bridge,
        }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))


class UpdateBridge(RequestHandler):
    def post(self):

        if not can_control_gandalf():
            return

        action = self.request.get('action')
        bridge_name = self.request.get('bridge_name')

        if not bridge_name:
            raise Exception("Must include 'bridge_name' parameter")

        bridge = _GandalfBridge.get_or_insert(bridge_name)

        if action == 'delete':
            bridge.delete()

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

            if not filter_type:
                raise Exception("Must include 'filter_type' parameter")

            if not bridge_name:
                raise Exception("Must include 'bridge_name' parameter")

            try:
                bridge = _GandalfBridge.get_by_key_name(bridge_name)
            except BadValueError:
                raise Exception("Bridge '%s' does not exist" % bridge_name)

            context = BridgeFilter.find_subclass(filter_type).initial_context()

            filter = _GandalfFilter(bridge=bridge, filter_type=filter_type, context=context)
            filter.put()

        else:

            filter_key = self.request.get('filter_key')
            
            if not filter_key:
                raise Exception("Must include 'filter_key' parameter")

            filter = _GandalfFilter.get(filter_key)

            if action == "delete":

                filter.delete()

            elif action == "save":

                whitelist = self.request.get('whitelist')

                try:
                    percentage = int(self.request.get('percentage'))

                    if 0 <= percentage <= 100:
                        filter.percentage = percentage

                except ValueError:
                    pass

                filter.whitelist = whitelist == "true"

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
