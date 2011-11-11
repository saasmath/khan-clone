from __future__ import with_statement
import os

def find_subclass(filter_type):
    for subclass in BridgeFilter.__subclasses__():
        if subclass.name == filter_type:
            return subclass

class BridgeFilter(object):

    @staticmethod
    def passes(context, user_data):
        raise NotImplementedError("Should have implemented this")

    @staticmethod
    def initial_context():
        raise NotImplementedError("Should have implemented this")

    @classmethod
    def proper_name(cls):
        return cls.name.replace("-", " ").capitalize()

    @classmethod
    def render(cls):
        path = os.path.join(os.path.dirname(__file__), "templates/filters/%s" % cls.filename)

        with open(path) as f:
            html = f.read()

        return html

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

class ClassroomBridgeFilter(BridgeFilter):
    name = "in-classroom"
    filename = "empty.html"

    @staticmethod
    def passes(context, user_data):
        return False

    @staticmethod
    def initial_context():
        return {}

