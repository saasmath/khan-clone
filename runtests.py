#!/usr/bin/env python

import optparse
import os
import sys
# Install the Python unittest2 package before you run this script.
import unittest2

USAGE = """%prog TEST_PATH [options]

Runs unit tests for App Engine apps.

This sets the appropriate Python PATH and environment. Tests files are
expected to be named with a _test.py suffix.

TEST_PATH   Path to package containing test modules or Python file
            containing test case.
"""


TEST_FILE_RE = '*_test.py'

def file_path_to_module(path):
    return path.replace('.py', '').replace(os.sep, '.')

def discover_sdk_path():
    # adapted from http://code.google.com/p/bcannon/source/browse/sites/py3ksupport-hrd/run_tests.py

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
    sys.path.append(app_engine_path)

def main(test_path):
    if 'SERVER_SOFTWARE' not in os.environ:
        os.environ['SERVER_SOFTWARE'] = 'Development'
    if 'CURRENT_VERSION' not in os.environ:
        os.environ['CURRENT_VERSION'] = '764.1'

    import dev_appserver
    dev_appserver.fix_sys_path()
    top_project_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    sys.path.insert(0, os.path.join(top_project_dir, "api/packages"))
    sys.path.insert(0, os.path.join(top_project_dir, "api/packages/flask.zip"))

    loader = unittest2.loader.TestLoader()
    if test_path.endswith('.py'):
        suite =  loader.loadTestsFromName(file_path_to_module(test_path))
    else:
        suite = loader.discover(test_path, pattern=TEST_FILE_RE)

    result = unittest2.TextTestRunner(verbosity=2).run(suite)
    return not result.wasSuccessful()

if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    parser.add_option('--sdk', dest='sdk', metavar='SDK_PATH',
                      help='path to the App Engine SDK')
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)
    TEST_PATH = args[0]

    if options.sdk:
        sys.path.append(options.sdk)
    else:
        discover_sdk_path()

    result = main(TEST_PATH)
    sys.exit(result)
