#!/bin/bash
# Double-click on macOS: serves the mirror and opens it in Chrome.
# Game logs (log=1) and server errors stream here; closing this window stops the server.
cd "$(dirname "$0")" || exit 1
PORT=${PORT:-8000}
# Minimum graphics; low=1 alone also drops to 2 engine cores, cores= keeps all of them.
# v=2 is a page URL that Chrome has not cached (see index.html); unknown parameters are ignored.
QUERY="?low=1&cores=$(sysctl -n hw.ncpu)&log=1&v=2"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    # A second launch must not rotate away the running session's log.
    echo "Port $PORT is already in use (the game server is probably running in another window)."
    read -r -p "Press Enter to close..."
    exit 1
fi
(sleep 1 && open -a "Google Chrome" "http://localhost:$PORT/$QUERY") &
# last-session.log holds this launch; the one before it moves to previous-session.log.
[ -s last-session.log ] && mv -f last-session.log previous-session.log
python3 -I -u serve_local.py --port "$PORT" 2>&1 | tee last-session.log
status=${PIPESTATUS[0]}

if [ "$status" -ne 0 ]; then
    echo
    echo "Server exited with code $status (port $PORT may already be in use)."
    read -r -p "Press Enter to close..."
fi
