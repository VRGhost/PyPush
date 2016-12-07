#!/bin/bash -xe

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}")

# Test & validate
"${BIN_DIR}/test.sh"
"${BIN_DIR}/pylint_score_guard.sh"

git checkout release
git merge --squash master
pip freeze "${PROJECT_DIR}/requirements/prod.txt" > "${PROJECT_DIR}/requirements/frozen.txt"
git add "${PROJECT_DIR}/requirements/frozen.txt"
git commit -m "Frozen requirements updated"

git checkout master