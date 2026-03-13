#!/bin/bash

set -euo pipefail

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

if command -v podman-compose >/dev/null 2>&1; then
    compose=podman-compose
else
    compose=docker-compose
fi

cleanup() {
    "$compose" down --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

# Always reset the compose stack managed by this service before starting it
"$compose" down --remove-orphans >/dev/null 2>&1 || true

"$compose" up -d --build
"$compose" ps

./monitor.sh ./transform_txt.py "$DSTDIR/Text" "$DSTDIR"

# sba-txt-service.sh ends here
