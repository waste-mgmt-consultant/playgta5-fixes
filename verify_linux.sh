#!/bin/bash
# Verifies that the Linux setup is complete and correct.
# Usage: ./verify_linux.sh
set -u
cd "$(dirname "$0")" || exit 1
ok=0; fail=0
pass() { echo "  [ OK ] $1"; ok=$((ok+1)); }
bad()  { echo "  [FAIL] $1"; fail=$((fail+1)); }

echo "playgta5-fixes — Linux setup check"
echo "----------------------------------"

# 1. Python
if command -v python3 >/dev/null 2>&1; then
    ver=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
    if python3 -c 'import sys;exit(0 if sys.version_info>=(3,11) else 1)'; then
        pass "python3 $ver (>= 3.11)"
    else
        bad "python3 $ver is too old (need >= 3.11)"
    fi
else
    bad "python3 not found"
fi

# 2. Game data
if [ -f "mirror/playgta5.com/data/manifest.json" ]; then
    pass "game data present (mirror/playgta5.com/data/manifest.json)"
else
    bad "game data missing (mirror/playgta5.com/data/manifest.json)"
fi

# 3. Core engine files
for f in "mirror/playgta5.com/index.html" \
         "mirror/playgta5.com/b/8b0b5899ed/game.wasm" \
         "mirror/playgta5.com/b/8b0b5899ed/game.js" \
         "mirror/playgta5.com/b/8b0b5899ed/io_worker.js" \
         "mirror/playgta5.com/b/8b0b5899ed/loader.js"; do
    [ -f "$f" ] && pass "found $f" || bad "missing $f"
done

# 4. Fixed files match git (the three tracked fixes)
if git rev-parse --git-dir >/dev/null 2>&1; then
    if git diff --quiet -- mirror/playgta5.com/index.html \
                          mirror/playgta5.com/b/8b0b5899ed/io_worker.js \
                          mirror/playgta5.com/b/8b0b5899ed/loader.js 2>/dev/null; then
        pass "fixed files (index.html, io_worker.js, loader.js) match git"
    else
        bad "fixed files differ from git — run: git checkout -- mirror"
    fi
fi

# 5. game.wasm patched
WASM="mirror/playgta5.com/b/8b0b5899ed/game.wasm"
ORIG="mirror/playgta5.com/b/8b0b5899ed/game.wasm.orig"
if [ -f "$ORIG" ]; then
    pass "backup game.wasm.orig exists"
    if cmp -s "$WASM" "$ORIG"; then
        bad "game.wasm is UNPATCHED — run: ./patch.sh"
    else
        pass "game.wasm is patched (differs from .orig)"
    fi
else
    bad "game.wasm.orig missing — run: ./patch.sh"
fi

# 6. Server script
if python3 -c 'import ast,sys;ast.parse(open("serve_local.py").read())' 2>/dev/null; then
    pass "serve_local.py parses"
else
    bad "serve_local.py has syntax errors"
fi

# 7. Launcher executable
[ -x "Launch-Local.sh" ] && pass "Launch-Local.sh is executable" || bad "Launch-Local.sh not executable (chmod +x)"

echo "----------------------------------"
echo "Passed: $ok   Failed: $fail"
[ "$fail" -eq 0 ] && echo "RESULT: READY TO PLAY" || echo "RESULT: FIX THE ITEMS ABOVE"
exit "$fail"
