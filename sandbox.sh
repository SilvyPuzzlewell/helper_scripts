#!/bin/bash
set -e
if [ $# -lt 1 ]; then
    VENV_PATH=/home/ron/prace/nr-docs/.venv/bin/activate
else
    VENV_PATH=/home/ron/prace/$1/.venv/bin/activate
fi
SCRIPT_PATH=$(realpath "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")

. $VENV_PATH
cd $SCRIPT_DIR

for file in "$(pwd)"/current_token_*; do
  if [ -e "$file" ]; then
    echo "Deleting: $file"
  fi
done
