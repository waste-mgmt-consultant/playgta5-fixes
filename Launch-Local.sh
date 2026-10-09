#!/bin/bash
# Linux launcher for playgta5-fixes.
# Serves the mirror on http://localhost:8000/ and opens your browser.
# Game logs (?log=1) and server errors stream to this terminal.
# Press Ctrl+C to stop the server.
set -u
cd "$(dirname "$0")" || exit 1

PORT=${PORT:-8000}
CORES=${CORES:-$(nproc 2>/dev/null || echo 4)}
# Minimum graphics; low=1 alone also drops to 2 engine cores, cores= keeps all of them.
# v=2 is a page URL the browser has not cached (see index.html); unknown parameters are ignored.
QUERY="?low=1&cores=${CORES}&log=1&v=2"

# Pick a browser opener available on this system.
open_browser() {
    local url="$1"
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 &
    elif command -v gio >/dev/null 2>&1; then
        gio open "$url" >/dev/null 2>&1 &
    elif command -v sensible-browser >/dev/null 2>&1; then
        sensible-browser "$url" >/dev/null 2>&1 &
    elif command -v firefox >/dev/null 2>&1; then
        firefox "$url" >/dev/null 2>&1 &
    elif command -v google-chrome >/dev/null 2>&1; then
        google-chrome "$url" >/dev/null 2>&1 &
    elif command -v chromium >/dev/null 2>&1; then
        chromium "$url" >/dev/null 2>&1 &
    else
        echo "No browser opener found. Open this URL manually: $url"
    fi
}

# Refuse to start a second server on the same port.
if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ":${PORT}[[:space:]]"; then
    echo "Port $PORT is already in use (the game server is probably running in another window)."
    echo "Run with a different port, e.g.:  PORT=8080 ./Launch-Local.sh"
    exit 1
fi

echo "playgta5-fixes"
echo "Starting local server on http://localhost:$PORT/$QUERY"
echo "Press Ctrl+C to stop."
echo

(sleep 1 && open_browser "http://localhost:$PORT/$QUERY") &

# Keep the current session log; move the previous one aside.
[ -s last-session.log ] && mv -f last-session.log previous-session.log
python3 -I -u serve_local.py --port "$PORT" 2>&1 | tee last-session.log
status=${PIPESTATUS[0]}

if [ "$status" -ne 0 ]; then
    echo
    echo "Server exited with code $status (port $PORT may already be in use)."
fi
