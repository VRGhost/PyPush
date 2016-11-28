# Open Source Push Server

[![Build Status](https://travis-ci.org/VRGhost/PyPush.svg?branch=master)](https://travis-ci.org/VRGhost/PyPush)

A 3rd-party implementation of Microbot Push service.

This project is planned to contain three separate elements:
  * [python library](#microbot-push-library) to interact with Microbot Push devices via BLE
  * [daemon](#microbot-push-daemon) that handles most of the BLE-related chores (e.g. device discovery/pairing/etc)
  * [simple web interface](#web-ui) to interact with the daemon


## Microbot Push Library

Although the library is intended to operate with any BLE hardware or stack, only [Bluegiga](https://www.silabs.com/products/wireless/bluetooth/bluetooth-smart-modules/Pages/bled112-bluetooth-smart-dongle.aspx) stack is supported for the moment.

[Microbot Push Library Documentation](docs/PyPush_lib.md)

## Microbot Push Daemon
Not available yet.

## Web UI
Not available yet.