#!/bin/bash -e

# This returns a non-zero return code when pylint's score
#  for this project falls below TARGET_SCORE

TARGET_SCORE=6

BIN_DIR=$(python -c "import os.path as p ; print p.dirname(p.realpath('${BASH_SOURCE[0]}'))")
PROJECT_ROOT=$(dirname "${BIN_DIR}")
TEST_DIR="${PROJECT_ROOT}/tests"
LOGFILE="${PROJECT_ROOT}/_tmp/pylint_out.log"

cd "${PROJECT_ROOT}"

$(python -m pylint PyPush > "${LOGFILE}" ) || sleep 0 # This hides pylint's exit code from 'bash -e'
CODE_RATING=$(cat "${LOGFILE}" | grep 'Your code has been rated at' | sed 's/\// /g' | sed 's/[^0-9. ]//g' | sed 's/  */ /g' | cut -d ' ' -f 2)
RC=0

echo "Pylint score is ${CODE_RATING}"

if [ $(echo "${CODE_RATING} < ${TARGET_SCORE}" | bc) -eq 1 ]; then
    cat "${LOGFILE}"
    echo "-------- PyLint score is below ${TARGET_SCORE} (the actual score is ${CODE_RATING}) ---------"
    RC=1
fi

rm "${LOGFILE}"

exit ${RC}