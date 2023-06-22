#!/bin/bash

set -e

cd "$(dirname "$0")"

USER=$(id -nu)
GROUP=$(id -ng)

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

sudo systemctl enable $PWD/sba-md.service
sudo systemctl start sba-md.service
sudo systemctl status sba-md.service

# install-systemd-services.sh ends here
