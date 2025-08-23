#!/bin/bash

DIR="$(dirname "$0")"

cd "$DIR" || exit 1

if [ ! -r .env ]; then
    echo "Create a .env from example.env" 1>&2
    exit 1
fi

. .env

# Check if required environment variables are set
if [ -z "$DSTDIR" ]; then
    echo "Please set DSTDIR in .env" 1>&2
    exit 1
fi

mkdir -p "$DSTDIR/Chunk" "$DSTDIR/Db"

if type -p podman-compose; then
    compose=podman-compose
else
    compose=docker-compose
fi

set -e

# Check if container is already running and stop it if needed
if $compose ps | grep -q "Up"; then
    echo "Container is already running, stopping it first..."
    $compose down
fi

$compose up -d
$compose ps

./monitor.sh ./transform_txt.py "$DSTDIR/Text" "$DSTDIR"

# sba-txt-service.sh ends here
