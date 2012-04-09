"""
Annotations for unittest resource requirements

Decorate unit tests to indicate the difference between small, fast
tests and big, slow tests. Test runners will skip sizes that are not
allowed to run. By default, all test sizes run.

Test sizing guide:

 - Small tests run in less than one second
 - Medium tests run in less than one minute
 - Large tests run in one minute or more
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

SMALL_SIZE = 1
MEDIUM_SIZE = 2
LARGE_SIZE = 4

ALLOWED_SIZES = SMALL_SIZE | \
                MEDIUM_SIZE | \
                LARGE_SIZE
"""Tests of these sizes are allowed to run"""


def small():
    """Skip unless small sized tests are allowed to run"""
    if ALLOWED_SIZES & SMALL_SIZE:
        return lambda func: func
    return unittest.skip("skipping small tests")


def medium():
    """Skip unless medium sized tests are allowed to run"""
    if ALLOWED_SIZES & MEDIUM_SIZE:
        return lambda func: func
    return unittest.skip("skipping medium tests")


def large():
    """Skip unless large sized tests are allowed to run"""
    if ALLOWED_SIZES & LARGE_SIZE:
        return lambda func: func
    return unittest.skip("skipping large tests")
