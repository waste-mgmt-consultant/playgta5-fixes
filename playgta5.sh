#!/bin/bash
# playgta5 — one command to manage the playgta5-fixes Linux installation.
#
#   ./playgta5.sh start      Start the local server and open the browser
#   ./playgta5.sh lan        Serve to other devices on your network
#   ./playgta5.sh patch      Apply the game.wasm fixes (shop/crash/money)
#   ./playgta5.sh verify     Check that everything is installed correctly
#   ./playgta5.sh doctor     Full health check (install + browser + server)
#   ./playgta5.sh status     Show install + server status
#   ./playgta5.sh stop       Stop a running local server
#   ./playgta5.sh shortcut   (Re)install the desktop shortcut
#   ./playgta5.sh setup      Run the one-shot setup (extract + merge + patch)
#   ./playgta5.sh help       Show this help
set -u
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO" || exit 1

WASM="mirror/playgta5.com/b/8b0b5899ed/game.wasm"
ORIG="mirror/playgta5.com/b/8b0b5899ed/game.wasm.orig"
MANIFEST="mirror/playgta5.com/data/manifest.json"
PORT="${PORT:-8000}"

banner() { echo "playgta5-fixes ($1)"; echo "----------------------------------------"; }

case "${1:-help}" in
  start)
    banner "start"
    exec bash Launch-Local.sh
    ;;
  lan)
    banner "lan"
    exec bash Launch-LAN.sh
    ;;
  patch)
    banner "patch"
    exec bash patch.sh
    ;;
  verify)
    banner "verify"
    bash verify_linux.sh
    ;;
  browser)
    banner "browser"
    bash check_browser.sh
    ;;
  doctor)
    banner "doctor"
    echo "--- installation ---"
    bash verify_linux.sh || true
    echo
    echo "--- snapshot (12,482 files + live server tests) ---"
    python3 verify_snapshot.py > /tmp/opencode/doctor-snapshot.log 2>&1 \
      && echo "snapshot: PASSED (see snapshot/verification.json)" \
      || { echo "snapshot: FAILED — see /tmp/opencode/doctor-snapshot.log"; tail -5 /tmp/opencode/doctor-snapshot.log; }
    echo
    echo "--- browser ---"
    bash check_browser.sh || true
    echo
    echo "--- status ---"
    "$0" status
    ;;
  shortcut)
    banner "shortcut"
    bash install-shortcut.sh
    ;;
  setup)
    banner "setup"
    bash setup_linux.sh
    ;;
  stop)
    banner "stop"
    # Brackets stop pgrep from matching this script's own command line.
    pids=$(pgrep -f "[s]erve_local.py" 2>/dev/null || true)
    if [ -z "$pids" ]; then
      echo "No local server is running."
    else
      echo "Stopping server (PID: $pids)..."
      kill $pids 2>/dev/null || true
      sleep 1
      pgrep -f "serve_local.py" >/dev/null 2>&1 && kill -9 $(pgrep -f "serve_local.py") 2>/dev/null || true
      echo "Stopped."
    fi
    ;;
  status)
    banner "status"
    # Python
    if command -v python3 >/dev/null 2>&1; then
      echo "Python:        $(python3 --version 2>&1)"
    else
      echo "Python:        NOT FOUND"
    fi
    # Game data
    if [ -f "$MANIFEST" ]; then
      echo "Game data:     present ($(du -sh mirror 2>/dev/null | cut -f1))"
    else
      echo "Game data:     MISSING ($MANIFEST)"
    fi
    # Wasm patch state
    if [ -f "$WASM" ] && [ -f "$ORIG" ]; then
      if cmp -s "$WASM" "$ORIG"; then
        echo "game.wasm:     UNPATCHED  -> run: ./playgta5.sh patch"
      else
        echo "game.wasm:     patched    ($(stat -c%s "$WASM" 2>/dev/null) bytes)"
      fi
    else
      echo "game.wasm:     not installed yet"
    fi
    # ZIP present?
    if [ -f "GTA5Webport.zip" ]; then
      echo "ZIP:           present ($(du -h GTA5Webport.zip | cut -f1)) — delete after verifying"
    else
      echo "ZIP:           removed (space reclaimed)"
    fi
    # Server
    if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ":${PORT}[[:space:]]"; then
      echo "Server:        RUNNING on http://localhost:$PORT/"
    else
      echo "Server:        stopped"
    fi
    # Saves
    n=$(ls -1 save-backups/live 2>/dev/null | wc -l)
    echo "Saved games:   $n file(s) in save-backups/live/"
    echo "Disk free:     $(df -h . | awk 'NR==2{print $4}')"
    ;;
  help|--help|-h)
    banner "help"
    awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
    echo
    echo "Environment overrides: PORT=8080 CORES=8 ./playgta5.sh start"
    ;;
  *)
    echo "Unknown command: $1"
    echo "Run: ./playgta5.sh help"
    exit 1
    ;;
esac
