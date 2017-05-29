#!/bin/bash

DOCKER_BIN_DIR=$(dirname "${BASH_SOURCE[0]}")

cd "${DOCKER_BIN_DIR}/../.." # cd to the project's root

HOST_STARTUP_SCRIPT="${HOST_MOUNDED_DIR}/startup.sh"
HOST_EXIT_SCRIPT="${HOST_MOUNDED_DIR}/exit.sh"



if [[ -f "${HOST_STARTUP_SCRIPT}" ]]
then
    echo "Executing ${HOST_STARTUP_SCRIPT}"
    sh -c "${HOST_STARTUP_SCRIPT}" # Execute the script
else
    echo "Host startup script ${HOST_STARTUP_SCRIPT} not found"
fi

"./bin/serve.sh" \
    --ble_driver "${DRIVER}" \
    --ble_device "${DEVICE}" \
    --db_uri "sqlite:///${HOST_MOUNDED_DIR}/py_push_db.sqlite" \
    web_ui --host 0.0.0.0 --port "${PORT}"  \
    --application_root "${APPLICATION_ROOT}" 

if [[ -f "${HOST_EXIT_SCRIPT}" ]]
then
    echo "Executing ${HOST_EXIT_SCRIPT}"
    sh -c "${HOST_EXIT_SCRIPT}" # Execute the script
else
    echo "Host exit script ${HOST_EXIT_SCRIPT} not found"
fi