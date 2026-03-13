SHELL := /bin/bash
UV := UV_CACHE_DIR=/tmp/uv-cache uv

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
	$(UV) sync --all-extras
	touch uv.lock

.PHONY: sync-test test test-unit test-integration

sync-test:
	$(UV) sync --extra test

test: sync-test
	$(UV) run pytest

test-unit: sync-test
	$(UV) run pytest -m "not integration"

test-integration: sync-test
	$(UV) run pytest -m integration
