#!/bin/bash

SRC="$1"
DST="$2"

set -x

./transform.py "$SRC" "$DST"

inotifywait -m -e CLOSE_WRITE "$SRC"|while read line; do echo "$line"; ./transform.py "$SRC" "$DST"; done

# monitor.sh ends here
