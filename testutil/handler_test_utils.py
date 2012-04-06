"""
Utilities for end-to-end tests on handlers.

end-to-end tests are tests that send a url to a running server and get
a response back, and check that response to make sure it is 'correct'.

If you wish to write such tests, they should be in a file all their
own, perhaps named <file>_endtoend_test.py, and that file should start with:
   from testutil import handler_test_utils
   def setUpModule():
       handler_test_utils.start_dev_appserver()
   def tearDownModule():
       handler_test_utils.stop_dev_appserver()

TODO(csilvers): figure out if we can share this among many end-to-end
tests.  Maybe have each test that needs it advertise that fact, so it
will start up if necessary, and then somehow tell the test-runner to
call stop_dev_appserver() at test-end time.

TODO(csilvers): figure out how to reset the datastore between tests,
so there are no side-effects.

Note that these end-to-end tests are quite slow, since it's not a fast
operation to create a dev_appserver instance!

dev_appserver.py must be on your path.  The tests you run here must be
run via toosl/runtests.py, so the appengine path can be set up
correctly.

Also note that the dev_appserver instance, by default, is created in a
'sandbox' with no datastore contents.
TODO(csilvers): create some 'fake' data that can be used for testing.

Useful variables:
   appserver_url: url to access the running dev_appserver instance,
      e.g. 'http://localhost:8080'
"""

import os
import shutil
import socket
import subprocess
import tempfile
import time

appserver_url = None


# Vars used only internally, to communicate between start() and stop().
_tmpdir = None
_pid = None

def start_dev_appserver():
    """Starts up a dev-appserver instance on an unused port."""
    global appserver_url, _tmpdir, _pid

    # Find the 'root' directory of the project the tests are being
    # run in.
    ka_root = os.getcwd()
    while ka_root != os.path.dirname(ka_root):   # we're not at /
        if os.path.exists(os.path.join(ka_root, 'app.yaml')):
            break
        ka_root = os.path.dirname(ka_root)
    if not os.path.exists(os.path.join(ka_root, 'app.yaml')):
        raise IOError('Unable to find app.yaml above cwd: %s' % os.getcwd())

    # Create a 'sandbox' directory that symlinks to ka_root,
    # except for the 'datastore' directory (we don't want to mess
    # with your actual datastore for these tests!)
    _tmpdir = tempfile.mkdtemp()
    for f in os.listdir(ka_root):
        if 'datastore' not in f:
            os.symlink(os.path.join(ka_root, f),
                       os.path.join(_tmpdir, f))
    os.mkdir(os.path.join(_tmpdir, 'datastore'))

    # Find an unused port to run the appserver on.  There's a small
    # race condition here, but we can hope for the best.  Too bad
    # dev_appserver doesn't allow input to be port=0!
    for port in xrange(9000, 19000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        try:
            sock.connect(('', port))
            del sock   # reclaim the socket
        except socket.error:   # means nothing is running on that socket!
            dev_appserver_port = port
            break
    else:     # for/else: if we got here, we never found a good port
        raise IOError('Could not find an unused port in range 9000-19000')

    # Start dev_appserver
    args = ['dev_appserver.py',
            '-p%s' % dev_appserver_port,
            '--use_sqlite',
            '--high_replication',
            '--address=0.0.0.0',
            ('--datastore_path=%s'
             % os.path.join(_tmpdir, 'datastore/test.sqlite')),
            ('--blobstore_path=%s'
             % os.path.join(_tmpdir, 'blobs')),
            _tmpdir]
    # TODO(csilvers): redirect stdout/stderr somewhere so the output
    #                 isn't so noisy?  Maybe to a cStringIO object.
    _pid = subprocess.Popen(args).pid

    # Wait for the server to start up
    time.sleep(1)          # it *definitely* takes at least a second
    for i in xrange(40):   # wait for 8 seconds, until we give up
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        try:
            sock.connect(('', dev_appserver_port))
            break
        except socket.error:
            del sock   # reclaim the socket
            time.sleep(0.2)

    # Set the useful variables for subclasses to use
    global appserver_url
    appserver_url = 'http://localhost:%d' % dev_appserver_port

def stop_dev_appserver():
    global dev_appserver_url, _tmpdir, _pid

    # Try very hard to kill the dev_appserver process.
    if _pid:
        try:
            os.kill(_pid, 15)
            time.sleep(1)
            os.kill(_pid, 15)
            time.sleep(1)
            os.kill(_pid, 9)
        except OSError:   # Probably 'no such process': the kill succeeded!
            pass
        _pid = None

    # Now delete the tmpdir we made.
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)
        _tmpdir = None

    # We're done tearing down!
    dev_appserver_url = None
