"""Routines to ease dealing with appengine transactions."""

import os
from google.appengine.ext import db


def ensure_in_transaction(func, xg_on=False):
    """ Runs the specified method in a transaction, if the current thread is
    not currently running in a transaction already.

    However, if we're running as part of the remote-api service, do
    *not* run in a transaction, since remote-api does not support
    transactions well (in particular, you can't do any queries while
    inside a transaction).  The remote-api shell marks itself in the
    SERVER_SOFTWARE environment variable; other remote-api users
    should do similarly.
    """
    if db.is_in_transaction() or 'remote' in os.environ["SERVER_SOFTWARE"]:
        return func()
    
    if xg_on:
        options = db.create_transaction_options(xg=True)
        return db.run_in_transaction_options(options, func)
    else:
        return db.run_in_transaction(func)

