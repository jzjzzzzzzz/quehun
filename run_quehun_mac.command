#!/bin/zsh
set -e

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Missing .venv/bin/python. Create the environment and install requirements first."
  exit 1
fi

echo "Running macOS permission check..."
.venv/bin/python tools/macos_permissions.py || true

echo
echo "Starting QueHun visual control panel..."
.venv/bin/python main.py --gui
