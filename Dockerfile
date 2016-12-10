FROM python:2.7

ENV PORT=5000
ENV DEVICE="/dev/tty.usbmodem1"

RUN mkdir -p /usr/src
COPY ./ /usr/src/PyPush

WORKDIR /usr/src/PyPush

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE $PORT
CMD ["./bin/serve.sh", "--port", $PORT, "--ble_device", $DEVICE]