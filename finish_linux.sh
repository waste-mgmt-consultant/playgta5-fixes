#!/bin/bash
# Finalize the Linux installation: verify everything and print a summary.
# (The 21 GB GTA5Webport.zip was already removed; this script deletes nothing.)
set -u
cd "$(dirname "$0")" || exit 1
echo "[finalize] running installation check..."
bash verify_linux.sh
echo
echo "[finalize] running browser check..."
bash check_browser.sh || true
echo
echo "[finalize] status:"
bash playgta5.sh status
echo "[finalize] DONE — launch with ./playgta5.sh start (or double-click Play GTA5)"
