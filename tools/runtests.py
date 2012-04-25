#!/usr/bin/env python

import optparse
import os
import sys
# For python2.5 install the unittest2 package
try:   # Work under either python2.5 or python2.7
    import unittest2 as unittest
except ImportError:
    import unittest

import xmlrunner
import npm

USAGE = """%prog [options] [TEST_SPEC]

Run unit tests for App Engine apps.

This script will set up the Python path and environment. Test files
are expected to be named with a _test.py suffix.

TEST_SPEC   Specify tests by directory, file, or dotted name. Omit to
            use the current directory.

            Directory name: recursively search for files named *_test.py

            File name: find tests in the file.

            Dotted name: find tests specified by the name, e.g.,
            auth.tokens_test.TimestampTests.test_timestamp_creation,
            importer.autonow_test
"""


TEST_FILE_RE = '*_test.py'


def file_path_to_module(path):
    return path.replace('.py', '').replace(os.sep, '.')


def _discover_sdk_path():
    """Return directory from $PATH where the Google Appengine DSK lives."""
    # adapted from {http://code.google.com/p/bcannon/source/browse/
    # sites/py3ksupport-hrd/run_tests.py}

    # Poor-man's `which` command.
    for path in os.environ['PATH'].split(':'):
        if os.path.isdir(path) and 'dev_appserver.py' in os.listdir(path):
            break
    else:
        raise RuntimeError("couldn't find appcfg.py on $PATH")

    # Find out where App Engine lives so we can import it.
    app_engine_path = os.path.join(os.path.dirname(path), 'google_appengine')
    if not os.path.isdir(app_engine_path):
        raise RuntimeError('%s is not a directory' % app_engine_path)
    return app_engine_path


def fix_sys_path(appengine_sdk_dir=None):
    """Update sys.path for appengine and khan academy imports, also envvars."""
    if 'SERVER_SOFTWARE' not in os.environ:
        os.environ['SERVER_SOFTWARE'] = 'Development'
    if 'CURRENT_VERSION' not in os.environ:
        os.environ['CURRENT_VERSION'] = '764.1'

    if not appengine_sdk_dir:
        appengine_sdk_dir = _discover_sdk_path()
    sys.path.append(appengine_sdk_dir)
    import dev_appserver
    dev_appserver.fix_sys_path()

    top_project_dir = os.path.realpath(os.path.join(__file__, '../..'))
    sys.path.insert(0, top_project_dir)
    sys.path.insert(0, os.path.join(top_project_dir, "api/packages"))
    sys.path.insert(0, os.path.join(top_project_dir, "api/packages/flask.zip"))
    

def main(test_spec, should_write_xml, max_size, appengine_sdk_dir=None):
    fix_sys_path(appengine_sdk_dir)

    # This import needs to happen after fix_sys_path is run.
    from testutil import testsize
    testsize.set_max_size(max_size)

    if not npm.check_dependencies():
        return

    loader = unittest.loader.TestLoader()
    if not os.path.exists(test_spec):
        suite = loader.loadTestsFromName(test_spec)
    elif test_spec.endswith('.py'):
        suite = loader.loadTestsFromName(file_path_to_module(test_spec))
    else:
        suite = loader.discover(test_spec, pattern=TEST_FILE_RE)

    if should_write_xml:
        runner = xmlrunner.XMLTestRunner(verbose=True, output='test-reports')
    else:
        runner = unittest.TextTestRunner(verbosity=2)

    result = runner.run(suite)

    return not result.wasSuccessful()


if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    parser.add_option('--sdk', dest='sdk', metavar='SDK_PATH',
                      help='path to the App Engine SDK')
    parser.add_option('--max-size', dest='max_size', metavar='SIZE',
                      choices=['small', 'medium', 'large'],
                      default='medium',
                      help='run tests this size and smaller ("small", '
                           '"medium", "large")')
    parser.add_option('--xml', dest='xml', action='store_true',
                      help='write xUnit XML')

    options, args = parser.parse_args()

    if len(args) == 1:
        TEST_SPEC = args[0]
    else:
        TEST_SPEC = os.getcwd()

    result = main(TEST_SPEC, options.xml, options.max_size, options.sdk)
    sys.exit(result)
