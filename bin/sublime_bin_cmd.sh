#!/bin/bash -xe

# execution entery point for sublime text's scripts.
# The only difference to calling the script directly is implicit activation of the default virtualenv.

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}")

source "${PROJECT_ROOT}/.env/bin/activate"
exec $*