import copy_reg
from google.appengine.datastore import entity_pb
import types
import copy_reg


class PatchApplied(object):
    def __enter__(self,):
        # now monkey patch pickle.loads to try and get it working... uh-oh
        copy_reg._original_reconstructor = copy_reg._reconstructor
        copy_reg._reconstructor = _reconstructor_monkey_patch

    def __exit__(self, type, value, traceback):
        copy_reg._reconstructor = copy_reg._original_reconstructor


def _reconstructor_monkey_patch(cls, base, state):
    """The original version of _reconstructor only works with new style classes.

    Unfortunately, google.appengine.datastore.entity_pb.Reference changes from
    an old style class to a new style class in GAE Python 2.7. When depickling
    entity_pb.References, any that were pickled in Python 2.7 will not be
    readable by _reconstructor.

    This monkey patch adds a check to see if _reconstructor is passed a
    Reference that is an old-style class. If so, it instantiates it directly
    rather than calling object.__new__(). This works only for
    entity_pb.Reference objects.

    See the following pickled disassembly to for evidence this works:

    Python 2.7-pickled:

      5: c    GLOBAL     'copy_reg _reconstructor'
     30: p    PUT        2
    <snip>
    636: S    STRING     '_Key__reference'
    655: p    PUT        27
    659: g    GET        2
    662: (    MARK
    663: c        GLOBAL     'google.appengine.datastore.entity_pb Reference'
    711: p        PUT        28
    715: g        GET        4
    718: N        NONE
    719: t        TUPLE      (MARK at 662)
    720: R    REDUCE
    721: p    PUT        29
    725: S    STRING     'j\x0es~khan-academyr\x0f\x0b\x12\x05Video\x18\xe7\x8a\xa8\x8b\x01\x0c'
    798: b    BUILD
    799: s    SETITEM
    800: S    STRING     '_str'
    808: p    PUT        30
    812: N    NONE
    813: s    SETITEM
    814: b    BUILD
    815: s    SETITEM


    Python 2.5-pickled:

      5: c    GLOBAL     'copy_reg _reconstructor'
     30: p    PUT        1
    <snip>
    665: S    STRING     '_Key__reference'
    684: p    PUT        31
    688: (    MARK
    689: i        INST       'google.appengine.datastore.entity_pb Reference' (MARK at 688)
    737: p    PUT        32
    741: S    STRING     'j\x0es~khan-academyr\x0f\x0b\x12\x05Video\x18\xe7\x8a\xa8\x8b\x01\x0c'
    814: p    PUT        34
    818: b    BUILD
    819: s    SETITEM
    820: S    STRING     '_str'
    828: p    PUT        35
    832: N    NONE
    833: s    SETITEM
    834: b    BUILD


    """
    if base is object:
        if cls == entity_pb.Reference and type(cls) is types.ClassType:
            obj = cls()
        else:
            obj = object.__new__(cls)
    else:
        obj = base.__new__(cls, state)
        base.__init__(obj, state)
    return obj
