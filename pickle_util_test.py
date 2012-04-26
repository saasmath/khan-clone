"""Test pickle_util.py

In particular, test that we can successfully unpickle using the
pickle-map.
"""

import cPickle
import imp
import pickle
import sys
try:
    import unittest2 as unittest     # python 2.5
except ImportError:
    import unittest                  # python 2.6+

import pickle_util


class OldClass(object):
    _NAME = 'OldClass'

    def name(self):
        return self._NAME

    def num(self):
        return 1


class NewClassDefinition(object):
    _NAME = 'NewClass'

    def name(self):
        return self._NAME

    def num(self):
        return 1


# Now we want to install OldClassDefinition in its proper submodule
def setUpModule():
    """Install NewClassDefinition into its proper submodule."""
    mod = imp.new_module('mod')
    mod.submod1 = imp.new_module('submod1')
    mod.submod1.submod2 = imp.new_module('submod2')
    sys.modules['mod'] = mod
    sys.modules['mod.submod1'] = mod.submod1
    sys.modules['mod.submod1.submod2'] = mod.submod1.submod2
    mod.submod1.submod2.NewClass = NewClassDefinition


class PickleUtilTest(unittest.TestCase):
    def setUp(self):
        self.orig_class_rename_map = pickle_util._CLASS_RENAME_MAP
        self.orig_oldclass = OldClass

    def tearDown(self):
        pickle_util._CLASS_RENAME_MAP = self.orig_class_rename_map
        globals()['OldClass'] = self.orig_oldclass

    def test_simple(self):
        expected = 'i am a simple type'
        actual = pickle_util.load(pickle_util.dump(expected))
        self.assertEqual(expected, actual)

    def test_simple_class(self):
        """Test pickling and unpickling a class and class instance."""
        expected = (OldClass, OldClass())
        actual = pickle_util.load(pickle_util.dump(expected))
        self.assertEqual(expected[0], actual[0])
        self.assertEqual(type(expected[1]), type(actual[1]))

    def test_rewritten_class(self):
        global OldClass
        # Mock out the rename-map.
        pickle_util._CLASS_RENAME_MAP = {
            ('pickle_util_test', 'OldClass'):
            ('mod.submod1.submod2', 'NewClass')
            }
        pickled = pickle_util.dump(OldClass)
        # Just to make this more fun, delete OldClass
        del OldClass
        actual = pickle_util.load(pickled)
        import mod.submod1.submod2
        self.assertEqual(actual, mod.submod1.submod2.NewClass)

    def test_rewritten_class_instance(self):
        global OldClass
        # Mock out the rename-map.
        pickle_util._CLASS_RENAME_MAP = {
            ('pickle_util_test', 'OldClass'):
            ('mod.submod1.submod2', 'NewClass')
            }
        pickled = pickle_util.dump(OldClass())
        # Just to make this more fun, delete OldClass
        del OldClass
        actual = pickle_util.load(pickled)
        import mod.submod1.submod2
        self.assertTrue(isinstance(actual, mod.submod1.submod2.NewClass))

    def test_unpickling_data_pickled_with_pickle(self):
        expected = 'This is a test string'
        actual = pickle_util.load(pickle.dumps(expected))
        self.assertEqual(expected, actual)

    def test_unpickling_data_pickled_with_cpickle(self):
        expected = 'This is a test string'
        actual = pickle_util.load(pickle.dumps(expected))
        self.assertEqual(expected, actual)

    def test_unpickling_data_pickled_with_pickle_vhigh(self):
        expected = 'This is a test string'
        actual = pickle_util.load(pickle.dumps(expected,
                                               pickle.HIGHEST_PROTOCOL))
        self.assertEqual(expected, actual)

    def test_unpickling_data_pickled_with_cpickle_vhigh(self):
        expected = 'This is a test string'
        actual = pickle_util.load(cPickle.dumps(expected,
                                                cPickle.HIGHEST_PROTOCOL))
        self.assertEqual(expected, actual)

    def test_using_pickle_to_unpickle(self):
        expected = 'This is a test string'
        actual = pickle.loads(pickle_util.dump(expected))
        self.assertEqual(expected, actual)

    def test_using_cpickle_to_unpickle(self):
        expected = 'This is a test string'
        actual = cPickle.loads(pickle_util.dump(expected))
        self.assertEqual(expected, actual)
