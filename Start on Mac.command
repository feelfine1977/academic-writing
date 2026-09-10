#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  printf 'Run Install on Mac.command first.\n'
  exit 1
fi
exec .venv/bin/python desktop.py
