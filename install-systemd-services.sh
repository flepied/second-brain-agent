#!/bin/bash

set -e

cd "$(dirname "$0")"

USER=$(id -nu)
GROUP=$(id -ng)

if ! sudo systemctl status sba-md.service; then
    cat > sba-md.service <<EOF
[Unit]
Description=Transform Markdown files, pdf and Youtube transcripts for $USER into text files
DefaultDependencies=no
After=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
ExecStart=$PWD/sba-md-service.sh
TimeoutStartSec=0
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    sudo systemctl enable "$PWD/sba-md.service"
    sudo systemctl start sba-md.service
    sudo systemctl status sba-md.service
fi

if ! sudo systemctl status sba-txt.service; then
    cat > sba-txt.service <<EOF
[Unit]
Description=Transform txt files into chunks and then into embeddings in a vector db for $USER
DefaultDependencies=no
After=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
ExecStart=$PWD/sba-txt-service.sh
TimeoutStartSec=0
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    sudo systemctl enable $PWD/sba-txt.service
    sudo systemctl start sba-txt.service
    sudo systemctl status sba-txt.service
fi

# install-systetxt-services.sh ends here
