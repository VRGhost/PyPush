#!/bin/sh -x

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}"
)
cd "${PROJECT_ROOT}"
docker build -t vrghost/pypush:latest .
docker push vrghost/pypush