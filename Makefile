SHELL=/bin/bash

all: docker-compose.yml

docker-compose.yml: poetry.lock
	VER=$$(poetry run pip freeze|grep chromadb-client==|sed "s/.*==//") && echo $$VER && sed -i -e "s@ghcr.io/chroma-core/chroma:.*@ghcr.io/chroma-core/chroma:$$VER@" docker-compose.yml
