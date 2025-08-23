#!/bin/bash

cd $(cd "$(dirname "$0")" && pwd) || exit 1

# Check if the virtual environment exists and is readable
if [ ! -r .venv/bin/activate ]; then
    echo "Create a virtual environment with 'poetry install'" 1>&2
    exit 1
fi

. .venv/bin/activate

exec python mcp_server.py "$@"

# mcp-server.sh ends here
