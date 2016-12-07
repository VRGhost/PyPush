#!/bin/bash -xe

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}")
REQ_DIR="${PROJECT_ROOT}/requirements"

# Test & validate
"${BIN_DIR}/test.sh"
"${BIN_DIR}/pylint_score_guard.sh"

git checkout release
git merge --squash master
pip freeze "${REQ_DIR}/prod.txt" > "${REQ_DIR}/frozen.txt"
git add "${REQ_DIR}/frozen.txt"
git commit -m "Frozen requirements updated"

git checkout master