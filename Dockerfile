FROM python:2.7

ENV PORT=5000
ENV DRIVER="bluegiga"
ENV DEVICE="/dev/ttyACM*"
ENV APPLICATION_ROOT="/microbots"

RUN mkdir -p /usr/src
COPY ./ /usr/src/PyPush

RUN mkdir /usr/src/PyPush/host_mounted
VOLUME [ "/usr/src/PyPush/host_mounted" ]
WORKDIR /usr/src/PyPush

RUN rm -rf .git
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE $PORT
CMD [ "sh", "-c", "./bin/serve.sh --ble_driver \"${DRIVER}\" --ble_device \"${DEVICE}\" --db_uri \"sqlite:////usr/src/PyPush/host_mounted/py_push_db.sqlite\" web_ui --host 0.0.0.0 --port \"${PORT}\"  --application_root \"${APPLICATION_ROOT}\" " ]