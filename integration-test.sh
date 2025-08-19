#!/bin/bash

set -ex

if [ -f /etc/redhat-release ]; then
    sudo dnf install -y inotify-tools docker-compose
else
    sudo apt-get install inotify-tools docker-compose
fi

TOP=$(mktemp -d -p $HOME)
SRCDIR=$TOP/Notes
DSTDIR=$TOP/.second-brain

mkdir -p $SRCDIR $DSTDIR

# avoid losing my local env if testing locally :-)
test ! -f .env

cat > .env <<EOF
SRCDIR=$SRCDIR
DSTDIR=$DSTDIR
EOF

bash -x ./install-systemd-services.sh

sleep 5

if type -p podman-compose; then
    compose=podman-compose
else
    compose=docker-compose
fi

# wait for chromadb to be started
TRY=0
while [ $TRY -lt 30 ]; do
     TRY=$(( TRY + 1 ))
    if $compose ps | grep -q " Up "; then
        echo "*** Found finished marker"
        break
     fi
    sleep 1
done
$compose ps
$compose ps | grep -q " Up "

TRY=0
while [ $TRY -lt 24 ]; do
     TRY=$(( TRY + 1 ))
    if $compose logs | grep -q "Connect to Chroma at: "; then
        echo "*** Found finished marker"
        break
     fi
    sleep 5
done
$compose logs
$compose logs | grep -q "Connect to Chroma at: "

# create the document
cat > $SRCDIR/langchain.md <<EOF
## References

- https://docs.langchain.com/docs/
- https://blog.langchain.dev/conversational-retrieval-agents/

Plan-and-Solve Prompting: Improving Zero-Shot
Chain-of-Thought Reasoning by Large Language Models
https://arxiv.org/pdf/2305.04091.pdf
EOF

# wait for the document to be processed in sba-md
TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep -q "processed '$SRCDIR/langchain.md'"; then
        echo "*** Found finished marker"
        break
    fi
    journalctl --user -u sba-md
    sleep 1
done
journalctl --user -u sba-md
journalctl --user -u sba-md | grep "processed '$SRCDIR/langchain.md'"

# wait for the document to be processed in sba-txt
TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-txt | grep "Storing .* chunks to the db for metadata=.*'url': 'file://$SRCDIR/langchain.md'"|grep -q "'type': 'notes'"; then
        echo "*** Found finished marker"
        break
    fi
    journalctl --user -u sba-txt
    sleep 1
done

journalctl --user -u sba-txt
journalctl --user -u sba-txt | grep "Storing .* chunks to the db for metadata=.*'url': 'file://$SRCDIR/langchain.md'"|grep "'type': 'notes'"

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

# restart the container to be sure to have stored the information on disk
$compose restart

TRY=0
while [ $TRY -lt 24 ]; do
     TRY=$(( TRY + 1 ))
    if $compose logs | grep -q "Connect to Chroma at: "; then
        echo "*** Found finished marker"
        break
     fi
    sleep 5
done
$compose logs
$compose logs | grep -q "Connect to Chroma at: "

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

touch $SRCDIR/langchain.md

TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep "skipping $SRCDIR/langchain.md / .* as content did not change"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-md
jq . $TOP/.second-brain/checksums.json
journalctl --user -u sba-md | grep "skipping $SRCDIR/langchain.md / .* as content did not change"

# wait a bit to be sure to have all the logs in different seconds
# for the vacuum cleaning process to work
sleep 2

# test changing a document but not to all contents
sudo journalctl --user -u sba-md --rotate
sudo journalctl --user -u sba-md --vacuum-time=1s

cat >> $SRCDIR/langchain.md <<EOF
## Links

- https://python.langchain.com/
EOF

TRY=0
while [ $TRY -lt 30 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep -q "processed '$SRCDIR/langchain.md'"; then
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

rm "$SRCDIR/langchain.md"

TRY=0
while [ $TRY -lt 5 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-md | grep -q "removing $TOP/Text/langchain.json as $SRCDIR/langchain.md do not exist anymore"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-md
journalctl --user -u sba-md | grep -q "removing $TOP/.second-brain/Text/langchain.json as $SRCDIR/langchain.md do not exist anymore"

TRY=0
while [ $TRY -lt 5 ]; do
    TRY=$(( TRY + 1 ))
    if journalctl --user -u sba-txt | grep -q "Removing .* related files to $TOP/.second-brain/Text/langchain.json:"; then
        echo "*** Found finished marker"
        break
    fi
    sleep 1
done
journalctl --user -u sba-txt
journalctl --user -u sba-txt | grep -q "Removing .* related files to $TOP/.second-brain/Text/langchain.json:"

# be sure we don't have anymore document in the vector database
poetry run ./similarity.py ""
poetry run ./similarity.py "" 2>&1 | grep "Number of documents in the vector store: 0"

# integration-test.sh ends here
