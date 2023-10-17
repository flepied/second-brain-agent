#!/bin/bash

DIR="$(dirname "$0")"

cd "$DIR" || exit 1

if [ ! -r .env ]; then
    echo "Create a .env from example.env" 1>&2
    exit 1
fi


. .env

mkdir -p "$DSTDIR/Chunk" "$DSTDIR/Db"

if type -p podman-compose; then
    compose=podman-compose
else
    compose=docker-compose
fi

set -e

$compose up -d
$compose ps

./monitor.sh ./transform_txt.py "$DSTDIR/Text" "$DSTDIR"

# sba-txt-service.sh ends here
