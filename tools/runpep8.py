#!/usr/bin/python

"""Run pep8 on every non-blacklisted python file under the current directory.

The arguments to this script are passed verbatim to pep8.  The only
difference between this script and running pep8 directly is you don't
give filenames to this script; it figures them out automatically from
the current working directory.  It uses runpep8_blacklist.txt to
exclude files from checking.
"""

import os
import sys
try:
    import pep8
except ImportError, why:
    sys.exit('FATAL ERROR: %s.  Install pep8 via "pip install pep8"' % why)


_BLACKLIST_FILE = os.path.join(os.path.dirname(__file__),
                               'runpep8_blacklist.txt')


# W291 trailing whitespace
# W293 blank line contains whitespace
_DEFAULT_PEP8_ARGS = ['--repeat',
                      '--ignore=W291,W293']


def _parse_blacklist(blacklist_filename):
    """Read from blacklist filename and returns a set of the contents.

    Blank lines and those that start with # are ignored.

    Arguments:
       blacklist_filename: the name of the blacklist file

    Returns:
       A set of all the paths listed in blacklist_filename.
       These paths may be filenames *or* directory names.
    """
    retval = set()
    contents = open(blacklist_filename).readlines()
    for line in contents:
        line = line.strip()
        if line and not line.startswith('#'):
            retval.add(line)
    return retval


def _files_to_process(rootdir, blacklist):
    """Return a set of .py files under rootdir not in the blacklist."""
    retval = set()
    for root, dirs, files in os.walk(rootdir):
        # Prune the subdirs that are in the blacklist.  We go
        # backwards so we can use del.  (Weird os.walk() semantics:
        # calling del on an element of dirs suppresses os.walk()'s
        # traversal into that dir.)
        for i in xrange(len(dirs) - 1, -1, -1):
            if os.path.join(root, dirs[i]) in blacklist:
                del dirs[i]
        # Take the files that end in .py and are not in the blacklist:
        for f in files:
            if f.endswith('.py') and os.path.join(root, f) not in blacklist:
                retval.add(os.path.join(root, f))
    return retval


def main(rootdir, pep8_args):
    """Run pep8 on all files in rootdir, using pep8_args as the flag-list."""
    blacklist = _parse_blacklist(_BLACKLIST_FILE)
    files = _files_to_process(rootdir, blacklist)
    pep8.process_options(pep8_args + list(files))
    for f in files:
        pep8.input_file(f)   # the weirdly-named function that does the work


if __name__ == '__main__':
    main('.', [sys.argv[0]] + _DEFAULT_PEP8_ARGS)
