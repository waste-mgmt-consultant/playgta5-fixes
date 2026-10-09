#!/bin/bash
# Applies the playgta5-fixes patch to game.wasm on Linux/macOS.
# Must be run before the first launch. Safe to run again.
set -eu
cd "$(dirname "$0")"
if [ ! -f "mirror/playgta5.com/b/8b0b5899ed/game.wasm" ]; then
    echo "game.wasm not found. Your mirror folder is missing or incomplete."
    echo "Expected at: mirror/playgta5.com/b/8b0b5899ed/game.wasm"
    exit 1
fi
python3 patch_shop_menus.py
