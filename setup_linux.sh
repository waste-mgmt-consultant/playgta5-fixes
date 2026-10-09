#!/bin/bash
# One-shot setup pipeline for Linux: waits for the ZIP extraction, merges the
# game data into place, restores the FIXED files, and patches game.wasm.
set -u
cd /home/mint/Desktop/playgta5-fixes || exit 1

echo "[setup] waiting for the ZIP extraction to finish..."
# Note: the bracket in "[u]nzip" stops pgrep from matching this script's own command line.
while pgrep -f "[u]nzip -o GTA5Webport.zip" >/dev/null 2>&1; do
    sleep 15
done
echo "[setup] extraction process finished"

if grep -qiE "^error|caution" /tmp/opencode/unzip.log 2>/dev/null; then
    echo "[setup] WARNING: unzip log may contain errors:"
    grep -iE "^error|caution" /tmp/opencode/unzip.log | head
fi

if [ ! -d "_staging/playgta5-offline/mirror" ]; then
    echo "[setup] ERROR: _staging/playgta5-offline/mirror not found. Aborting."
    exit 1
fi

echo "[setup] staged mirror size:"
du -sh _staging/playgta5-offline/mirror

echo "[setup] moving game data into place (preserving fixed files via git)..."
rm -rf mirror
mv _staging/playgta5-offline/mirror mirror
rm -rf _staging

echo "[setup] restoring the three FIXED files from git..."
git checkout -- mirror || echo "[setup] WARNING: git checkout failed; check fixed files manually"

echo "[setup] patching game.wasm..."
python3 patch_shop_menus.py

echo "[setup] verifying layout:"
ls -la mirror/playgta5.com/data/manifest.json mirror/playgta5.com/b/8b0b5899ed/game.wasm
du -sh mirror
echo "[setup] DONE"
