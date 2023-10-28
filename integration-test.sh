#!/bin/bash

set -ex

sudo apt-get install inotify-tools

mkdir $HOME/.second-brain $HOME/Notes

cat > .env <<EOF
SRCDIR=$HOME/Notes
DSTDIR=$HOME/.second-brain
EOF

bash -x ./install-systemd-services.sh

sleep 5

# wait for chromadb to be started
TRY=0
while [ $TRY -lt 30 ]; do
     TRY=$(( TRY + 1 ))
    if docker-compose ps | grep -q " Up "; then
        echo "*** Found finished marker"
        break
     fi
    sleep 1
done
docker-compose ps
docker-compose ps | grep -q " Up "

TRY=0
while [ $TRY -lt 24 ]; do
     TRY=$(( TRY + 1 ))
    if docker-compose logs | grep -q "Application startup complete"; then
        echo "*** Found finished marker"
        break
     fi
    sleep 5
done
docker-compose logs
docker-compose logs | grep -q "Application startup complete"

# create the document
cat > $HOME/Notes/langchain.md <<EOF
## References

- https://docs.langchain.com/docs/
- https://blog.langchain.dev/conversational-retrieval-agents/

Plan-and-Solve Prompting: Improving Zero-Shot
Chain-of-Thought Reasoning by Large Language Models
https://arxiv.org/pdf/2305.04091.pdf
EOF

# wait for the document to be processed
TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-txt | grep -q "Storing .* chunks to the db for metadata={'type': 'notes', 'url': 'file://$HOME/Notes/langchain.md'}'"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-md
journalctl --user -u sba-txt

journalctl --user -u sba-md | grep -q "processed '$HOME/Notes/langchain.md'"

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
sudo journalctl --user -u sba-md --rotate
sudo journalctl --user -u sba-md --vacuum-time=1s

touch $HOME/Notes/langchain.md

TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep "skipping $HOME/Notes/langchain.md / .* as content did not change"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-md
jq . $HOME/.second-brain/checksums.json
journalctl --user -u sba-md | grep "skipping $HOME/Notes/langchain.md / .* as content did not change"

# wait a bit to be sure to have all the logs in different seconds
# for the vacuum cleaning process to work
sleep 2

# test changing a document but not to all contents
sudo journalctl --user -u sba-md --rotate
sudo journalctl --user -u sba-md --vacuum-time=1s

cat >> $HOME/Notes/langchain.md <<EOF
## Links

- https://python.langchain.com/
EOF

TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep -q "processed '$HOME/Notes/langchain.md'"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-md

NB=$(journalctl --user -u sba-md | grep -c "content is the same for")

# pdf content is never processed again so the only ones are the 2 url
# in md doc
echo "*** NB=$NB"
test "$NB" -eq 2

# wait a bit to be sure to have all the logs in different seconds
# for the vacuum cleaning process to work
sleep 2

# test removing a document
sudo journalctl --user -u sba-md --rotate
sudo journalctl --user -u sba-md --vacuum-time=1s
sudo journalctl --user -u sba-txt --rotate
sudo journalctl --user -u sba-txt --vacuum-time=1s

rm "$HOME/Notes/langchain.md"

TRY=0
while [ $TRY -lt 5 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep -q "removing $HOME/Text/langchain.json as $HOME/Notes/langchain.md do not exist anymore"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-md
journalctl --user -u sba-md | grep -q "removing $HOME/.second-brain/Text/langchain.json as $HOME/Notes/langchain.md do not exist anymore"

TRY=0
while [ $TRY -lt 5 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-txt | grep -q "Removing .* related files to $HOME/.second-brain/Text/langchain.json:"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-txt
journalctl --user -u sba-txt | grep -q "Removing .* related files to $HOME/.second-brain/Text/langchain.json:"

# be sure we don't have anymore document in the vector database
poetry run ./similarity.py ""
poetry run ./similarity.py "" 2>&1 | grep "Number of documents in the vector store: 0"

# integration-test.sh ends here
