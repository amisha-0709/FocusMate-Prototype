#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m unittest -v test_server
node test_client_ai.js
python3 -m py_compile server.py test_server.py
git diff --check HEAD^ HEAD