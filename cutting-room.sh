#!/usr/bin/env sh
# macOS / Linux launcher: starts the cutting-room server (if it isn't already running) and opens the hub,
# or a project's editor if a project id is passed:  ./cutting-room.sh my-project
cd "$(dirname "$0")/engine" || exit 1
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
exec "$PY" serve.py --open "$@"
