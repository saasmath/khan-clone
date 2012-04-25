# From http://kovshenin.com/archives/app-engine-python-objects-in-the-google-datastore/

from google.appengine.ext import db

import pickle_util


# Use this property to store objects.
class ObjectProperty(db.BlobProperty):
    def validate(self, value):
        try:
            dummy = pickle_util.dump(value)
            return value
        except pickle_util.PicklingError, e:
            return super(ObjectProperty, self).validate(value)

    def get_value_for_datastore(self, model_instance):
        result = super(ObjectProperty, self).get_value_for_datastore(model_instance)
        result = pickle_util.dump(result)
        return db.Blob(result)

    def make_value_from_datastore(self, value):
        try:
            value = pickle_util.load(str(value))
        except:
            pass
        return super(ObjectProperty, self).make_value_from_datastore(value)


class UnvalidatedObjectProperty(ObjectProperty):
    def validate(self, value):
        # pickle.dumps can be slooooooow,
        # sometimes we just want to trust that the item is pickle'able.
        return value
