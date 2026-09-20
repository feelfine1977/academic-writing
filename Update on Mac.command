#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  printf 'Run Install on Mac.command first.\n'
else
  .venv/bin/python update.py
fi
printf '\nPress Return to close this window. '
read -r reply
