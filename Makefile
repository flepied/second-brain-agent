SHELL := /bin/bash

all: compose.yaml

compose.yaml: poetry.lock
	VER=$$(poetry run pip freeze|grep chromadb==|sed "s/.*==//") \
	&& poetry run pip freeze|grep chromadb \
	&& test -n "$$VER" \
	&& echo $$VER  _
	&& sed -i -e "s@ghcr.io/chroma-core/chroma:.*@ghcr.io/chroma-core/chroma:$$VER@" compose.yaml
