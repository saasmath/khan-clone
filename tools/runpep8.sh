#!/bin/bash

# Run from the app root to pep8 non-blacklisted files.
#
# This enables pep8 immediately for new files and existing files can be updated
# over time.  When a file is updated to pass pep8 remove it from the blacklist.

# The blacklist should live in the same directory as this script.
blacklist=`dirname "$0"`/runpep8_blacklist.txt

pep8_args="-r --ignore=W291,W293"

# To generate the blacklist:
# $ export LC_ALL=C
# $ find . -name '*.py' -print0 | xargs -0 pep8 ${pep8_args} | cut -d : -f 1 | sort -u
# (Note the LC_ALL=C makes the sort independent of locale on the machine
#  and makes this more consistent across developer machines)

# Lint files not in the blacklist.
export LC_ALL=C
find . -name "*.py" \
    | sort -u \
    | comm -23 - "${blacklist}" \
    | tr "\n" "\0" \
    | xargs -0 pep8 ${pep8_args} 

