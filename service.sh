#!/bin/bash

DIR="$(dirname "$0")"

cd "$DIR" || exit 1

./monitor.sh "$HOME/Notes/Notes" "$HOME/DocStore"

# service.sh ends here
