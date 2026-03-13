#!/bin/bash

set -e

dir=$(dirname $0)
cd "$dir"

. .venv/bin/activate

exec python "$dir/main.py" "$@"
