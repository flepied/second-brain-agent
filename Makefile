SHELL := /bin/bash

all: compose.yaml

compose.yaml: uv.lock
	set -x && \
	. .venv/bin/activate && \
	VER=$$(uv pip freeze|grep chromadb==|sed "s/.*==//") && \
	uv pip freeze && \
	test -n "$$VER" && \
	echo "$$VER" && \
	sed -i -e "s@ghcr.io/chroma-core/chroma:.*@ghcr.io/chroma-core/chroma:$$VER@" compose.yaml

uv.lock: pyproject.toml
	uv sync --all-extras
	touch uv.lock
