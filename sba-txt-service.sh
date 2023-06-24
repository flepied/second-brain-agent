#!/bin/bash

DIR="$(dirname "$0")"

cd "$DIR" || exit 1

if [ ! -r .env ]; then
    echo "Create a .env from example.env" 1>&2
    exit 1
fi

. .env

mkdir -p "$DSTDIR/Chunk" "$DSTDIR/Db"

./monitor.sh ./transform_txt.py "$DSTDIR/Text" "$DSTDIR"

# sba-txt-service.sh ends here