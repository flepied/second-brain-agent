#!/bin/bash

SRC="$1"
DST="$2"

set -x

cd $(dirname "$0") || exit 1

if [ ! -d .venv ]; then
    virtualenv .venv
fi

. .venv/bin/activate

./transform.py "$SRC" "$DST"

inotifywait -m -e CLOSE_WRITE "$SRC"|while read line; do echo "$line"; ./transform.py "$SRC" "$DST"; done

# monitor.sh ends here
