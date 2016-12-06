#!/bin/bash -x

WXPYTHON_APP="winpdb.py"
PYVER=2.7

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}")
TEST_DIR="${PROJECT_ROOT}/tests"

cd "${PROJECT_ROOT}"

if [ -z "$VIRTUAL_ENV" ] ; then
    echo "You must activate your virtualenv: set '$VIRTUAL_ENV'"
    exit 1
fi

SYSTEM_FRAMEWORK_PYTHON_ROOT="/Library/Frameworks/Python.framework/Versions/$PYVER"
# OS X 10.10
SYSTEM_FRAMEWORK_PYTHON_ROOT="/System$SYSTEM_FRAMEWORK_PYTHON_ROOT"

PYSUBVER="$(python --version 2>&1 | cut -d ' ' -f2)"  # e.g., 2.7.10
BREW_PYTHON_ROOT="$(brew --prefix)/Cellar/python/${PYSUBVER}_2/Frameworks/Python.framework/Versions/$PYVER"

PYTHON_BINARY="bin/python$PYVER"
#FRAMEWORK_PYTHON="$SYSTEM_FRAMEWORK_PYTHON_ROOT/$PYTHON_BINARY"

FRAMEWORK_PYTHON="$BREW_PYTHON_ROOT/$PYTHON_BINARY"

VENV_SITE_PACKAGES="$VIRTUAL_ENV/lib/python$PYVER/site-packages"

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Ensure wx.pth is set up in the virtualenv
cp "/Library/Python/$PYVER/site-packages/wxredirect.pth" "$VENV_SITE_PACKAGES/wx.pth"

# Use the Framework Python to run the app
export PYTHONHOME=$VIRTUAL_ENV
export PATH="${VENV_SITE_PACKAGES}:${PATH}"
exec "$FRAMEWORK_PYTHON" "$VENV_SITE_PACKAGES/$WXPYTHON_APP" $*