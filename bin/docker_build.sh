#!/bin/sh -x

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}")
cd "${PROJECT_ROOT}"

pushd _tmp
rm -rf *
git checkout .
popd

bower install
docker build -t vrghost/pypush:latest .
docker push vrghost/pypush

# Run with
#   
# docker pull vrghost/pypush
#  docker run --privileged=true -e DEVICE='/dev/ttyACM*' -v /volume3/docker/pypush:/usr/src/PyPush/host_mounted -e PORT='59730' -e APPLICATION_ROOT='/microbots' -p '59730:59730' -d --name pypush vrghost/pypush