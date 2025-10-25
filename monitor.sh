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
    echo "Virtual environment not found. Run 'uv sync --all-extras' first." 1>&2
    exit 1
fi

. .venv/bin/activate

"$TRANSFORM" "$SRC" "$DST"

echo "Finished processing $SRC ($TRANSFORM)"

inotifywait -m -e CLOSE_WRITE,DELETE "$SRC"|while read dir event fname; do
  echo "${dir}${fname} $event" 1>&2
  echo "${dir}${fname}"
done | "$TRANSFORM" "-" "$DST"

# monitor.sh ends here
