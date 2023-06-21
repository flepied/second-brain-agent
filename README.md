# tools to transform markdown files compatible with Obsidian to content files

Transforms markdown files compatible with Obsidian into content files extracting url automatically to get the content of the web page and the transcript of youtube videos as additional content.

## service

Create a service file in `/etc/systemd/system/md2content.service` replacing `fred` by your user:

```ini
[Unit]
Description=Transform Markdown docs, pdf and Youtube transcripts for fred into text files
DefaultDependencies=no
After=network.target

[Service]
Type=simple
User=fred
Group=fred
ExecStart=/home/fred/perso/md2content/service.sh
TimeoutStartSec=0
RemainAfterExit=yes

[Install]
WantedBy=default.target
```

Then add the service, with:

```ShellSession
# systemctl enable /etc/systemd/system/md2content.service
# systemctl start md2content
```

To see the output of the service:

```ShellSession
$ journalctl -f --unit=md2content.service
```
