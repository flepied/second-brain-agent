#!/bin/bash

DIR="$(dirname "$0")"

cd "$DIR" || exit 1

./monitor.sh /home/fred/Notes/Notes /home/fred/Content

# service.sh ends here
