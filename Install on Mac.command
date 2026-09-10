#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 install.py
printf '\nPress Return to close this window. '
read -r reply
