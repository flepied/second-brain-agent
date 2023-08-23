SHELL := /bin/bash

all: compose.yaml

compose.yaml: poetry.lock
	set -x && \
	. .venv/bin/activate && \
	VER=$$(pip3 freeze|grep chromadb==|sed "s/.*==//") && \
	pip3 freeze && \
	test -n "$$VER" && \
	echo "$$VER" && \
	sed -i -e "s@ghcr.io/chroma-core/chroma:.*@ghcr.io/chroma-core/chroma:$$VER@" compose.yaml

poetry.lock: pyproject.toml
	poetry lock --no-update
	touch poetry.lock
