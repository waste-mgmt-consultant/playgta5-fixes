#!/bin/bash
# Linux LAN launcher: serve playgta5-fixes to other machines on your network.
# On the client PC, open the printed http://<your-ip>:8080/ URL.
# WebGPU needs a secure context, so clients must whitelist that origin once
# (chrome://flags/#unsafely-treat-insecure-origin-as-secure). Press Ctrl+C to stop.
set -u
cd "$(dirname "$0")" || exit 1

PORT=${PORT:-8080}
CORES=${CORES:-$(nproc 2>/dev/null || echo 4)}
QUERY="?low=1&cores=${CORES}&log=1&v=2"

echo "playgta5-fixes — LAN server"
echo "Serving on port $PORT. Open one of these URLs on the client PC:"
if command -v hostname >/dev/null 2>&1 && hostname -I >/dev/null 2>&1; then
    for ip in $(hostname -I); do
        case "$ip" in
            127.*|::1) ;;
            *) echo "    http://$ip:$PORT/$QUERY" ;;
        esac
    done
fi
echo
echo "On each client, allow the insecure origin once in the browser:"
echo "  chrome://flags/#unsafely-treat-insecure-origin-as-secure"
echo "Add the exact origin, e.g. http://192.168.1.50:$PORT, then restart the browser."
echo "Press Ctrl+C to stop."
echo

[ -s last-session.log ] && mv -f last-session.log previous-session.log
python3 -I -u serve_local.py --host 0.0.0.0 --port "$PORT" 2>&1 | tee last-session.log
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
    echo
    echo "Server exited with code $status (port $PORT may already be in use)."
fi
