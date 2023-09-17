#!/bin/bash

set -ex

sudo apt-get install inotify-tools

mkdir $HOME/.second-brain $HOME/Notes

cat > .env <<EOF
SRCDIR=$HOME/Notes
DSTDIR=$HOME/.second-brain
EOF

cat > $HOME/Notes/langchain.md <<EOF
## References

- https://docs.langchain.com/docs/
- https://blog.langchain.dev/conversational-retrieval-agents/

Plan-and-Solve Prompting: Improving Zero-Shot
Chain-of-Thought Reasoning by Large Language Models
https://arxiv.org/pdf/2305.04091.pdf
EOF

bash -x ./install-systemd-services.sh

sleep 5

TRY=0
docker-compose ps
while [ $TRY -lt 24 ]; do
    TRY=$(( TRY + 1 ))
    if docker-compose logs | grep -q "Application startup complete"; then
        break
    fi
    docker-compose logs
    sleep 5
done

sudo journalctl -u sba-md
sudo journalctl -u sba-txt

cat > $HOME/Notes/langchain.md <<EOF
## References

- https://docs.langchain.com/docs/
- https://blog.langchain.dev/conversational-retrieval-agents/

Plan-and-Solve Prompting: Improving Zero-Shot
Chain-of-Thought Reasoning by Large Language Models
https://arxiv.org/pdf/2305.04091.pdf
EOF

# test the vector store
RES=$(poetry run ./similarity.py "What is langchain?")
echo "$RES"
test -n "$RES"

# test the vector store and llm
RES=$(poetry run ./qa.py "What is langchain?")
echo "$RES"
if grep -q "I don't know." <<< "$RES"; then
    exit 1
fi

# wait a bit to be sure to have all the logs in different seconds
# for the vacuum cleaning process to work
sleep 2

# test changing a document but not its content
sudo journalctl -u sba-md --rotate
sudo journalctl -u sba-md --vacuum-time=1s

touch $HOME/Notes/langchain.md

TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if sudo journalctl -u sba-md | grep -q "processed '$HOME/Notes/langchain.md'"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
sudo journalctl -u sba-md
jq . $HOME/.second-brain/checksums.json
sudo journalctl -u sba-md | grep "skipping $HOME/Notes/langchain.md / .* as content did not change"

# wait a bit to be sure to have all the logs in different seconds
# for the vacuum cleaning process to work
sleep 2

# test changing a document but not to all contents
sudo journalctl -u sba-md --rotate
sudo journalctl -u sba-md --vacuum-time=1s

cat >> $HOME/Notes/langchain.md <<EOF
## Links

- https://python.langchain.com/
EOF

TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if sudo journalctl -u sba-md | grep -q "processed '$HOME/Notes/langchain.md'"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
sudo journalctl -u sba-md

NB=$(sudo journalctl -u sba-md | grep -c "content is the same for")

# pdf content is never processed again so the only ones are the 2 url
# in md doc
echo "*** NB=$NB"
test "$NB" -eq 2

# integration-test.sh ends here
