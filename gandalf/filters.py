from __future__ import with_statement
import os

class BridgeFilter(object):
    filename = None

    @staticmethod
    def passes(context, user_data):
        raise NotImplementedError("Should have implemented this")

    @staticmethod
    def initial_context():
        return {}

    @classmethod
    def find_subclass(cls, filter_type):
        for subclass in cls.__subclasses__():
            if subclass.name == filter_type:
                return subclass

    @classmethod
    def get_filter_types(cls):
        return [{
            'proper_name': subclass.proper_name(),
            'name': subclass.name,
        } for subclass in cls.__subclasses__()]

    @classmethod
    def proper_name(cls):
        return cls.name.replace("-", " ").capitalize()

    @classmethod
    def render(cls):
        if not cls.filename:
            return ""

        path = os.path.join(os.path.dirname(__file__), "templates/filters/%s" % cls.filename)

        with open(path) as f:
            html = f.read()

        return html


class AllUsersBridgeFilter(BridgeFilter):
    name = "all-users"

    @staticmethod
    def passes(context, user_data):
        return True


class ProblemsDoneBridgeFilter(BridgeFilter):
    name = "problems-done"
    filename = "problems-done.html"

    @staticmethod
    def passes(context, user_data):
        return False

    @staticmethod
    def initial_context():
        return {
            'comp': '>=',
            'problems_done': 0,
        }


class HasCoachBridgeFilter(BridgeFilter):
    name = "has-coach"
    filename = "has-coach.html"

    @staticmethod
    def passes(context, user_data):
        return False

    @staticmethod
    def initial_context():
        return {
            'coach': 'true',
        }


class SpecificCoachesBirdgeFilter(BridgeFilter):
    name = "specific-coaches"
    filename = "specific-coaches.html"

    @staticmethod
    def passes(context, user_data):
        return False

    @staticmethod
    def initial_context():
        return {
            'coaches': "",
        }
