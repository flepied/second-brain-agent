#!/bin/bash

set -ex

sudo apt-get install inotify-tools

mkdir $HOME/.second-brain $HOME/Notes

cat > .env <<EOF
SRCDIR=$HOME/Notes
DSTDIR=$HOME/.second-brain
EOF

bash -x ./install-systemd-services.sh

cat > $HOME/Notes/langchain.md <<EOF
## References

- https://docs.langchain.com/docs/
- https://github.com/kyrolabs/awesome-langchain

Plan-and-Solve Prompting: Improving Zero-Shot
Chain-of-Thought Reasoning by Large Language Models
https://arxiv.org/pdf/2305.04091.pdf
EOF

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

set +x

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

# integration-test.sh ends here
