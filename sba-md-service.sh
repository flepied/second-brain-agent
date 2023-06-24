#!/bin/bash

DIR="$(dirname "$0")"

cd "$DIR" || exit 1

if [ ! -r .env ]; then
    echo "Create a .env from example.env" 1>&2
    exit 1
fi

. .env

mkdir -p "$DST/Orig" "$DST/Text"

./monitor.sh ./transform_md.py "$SRCDIR" "$DSTDIR"

# sba-md-service.sh ends here