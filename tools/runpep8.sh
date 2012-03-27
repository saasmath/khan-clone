#!/bin/bash

# Run from the app root to pep8 non-blacklisted files.
#
# This enables pep8 immediately for new files and existing files can be updated
# over time.  When a file is updated to pass pep8 remove it from the blacklist.

# The blacklist should live in the same directory as this script.
blacklist=`dirname "$0"`/runpep8_blacklist.txt

# To generate the blacklist:
# find . -name '*.py' -print0 | xargs -0 pep8 -r | cut -d : -f 1 | sort -u

# Lint files not in the blacklist.
find . -name "*.py" \
    | sort -u \
    | comm -23 - "${blacklist}" \
    | tr "\n" "\0" \
    | xargs -0 pep8 -r

