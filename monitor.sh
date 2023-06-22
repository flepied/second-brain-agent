#!/bin/bash

if [ $# != 3 ]; then
    echo "Usage: $0 <transform utility> <source dir> <target dir>" 1>&2
    exit 1
fi

TRANSFORM="$1"
SRC="$2"
DST="$3"

if [ ! -d "$SRC" ]; then
    echo "Source directory $SRC not found" 1>&2
    exit 1
fi

if [ ! -d "$DST" ]; then
    echo "Target directory $DST not found" 1>&2
    exit 1
fi

cd $(dirname "$0") || exit 1

if [ ! -d .venv ]; then
    python -m venv .venv
    pip install -r requirements.txt
fi

. .venv/bin/activate

mkdir -p "$DST/Orig" "$DST/Text"

./transform.py "$SRC" "$DST"

inotifywait -m -e CLOSE_WRITE "$SRC"|while read line; do echo "$line"; "$TRANSFORM" "$SRC" "$DST"; done

# monitor.sh ends here
