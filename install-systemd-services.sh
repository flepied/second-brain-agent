#!/bin/bash

set -e

cd "$(dirname "$0")"

if ! systemctl --user status sba-md.service; then
    cat > sba-md.service <<EOF
[Unit]
Description=Transform Markdown files, pdf and Youtube transcripts into text files
DefaultDependencies=no
After=network.target

[Service]
Type=simple
ExecStart=$PWD/sba-md-service.sh
TimeoutStartSec=0
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    systemctl --user enable "$PWD/sba-md.service"
    systemctl --user start sba-md.service
    systemctl --user status sba-md.service
fi

if ! systemctl --user status sba-txt.service; then
    cat > sba-txt.service <<EOF
[Unit]
Description=Transform txt files into chunks and then into embeddings in a vector db
DefaultDependencies=no
After=network.target

[Service]
Type=simple
ExecStart=$PWD/sba-txt-service.sh
TimeoutStartSec=0
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    systemctl --user enable $PWD/sba-txt.service
    systemctl --user start sba-txt.service
    systemctl --user status sba-txt.service
fi

# install-systetxt-services.sh ends here
