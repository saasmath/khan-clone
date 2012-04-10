from __future__ import with_statement

from google.appengine.ext import db
import pickle

from object_property import ObjectProperty as OriginalObjectProperty
from reconstructor_patch import ReconstructorPatch
import logging


class ObjectProperty(OriginalObjectProperty):
    def make_value_from_datastore(self, value):
        with ReconstructorPatch():
            try:
                value = pickle.loads(str(value))
            except Exception, e:
                logging.warn("ReconstructorPatch failed to depickle instance of type %r" % type(value))
                logging.warn(e)

        return super(db.BlobProperty, self).make_value_from_datastore(value)
