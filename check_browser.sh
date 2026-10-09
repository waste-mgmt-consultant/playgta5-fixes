#!/bin/bash
# Checks that this Linux machine has a browser capable of running the game.
# The game needs WebGPU + shared-memory WebAssembly (Chrome/Chromium 113+).
set -u
ok=0; fail=0
pass() { echo "  [ OK ] $1"; ok=$((ok+1)); }
bad()  { echo "  [FAIL] $1"; fail=$((fail+1)); }
info() { echo "  [info] $1"; }

echo "playgta5-fixes — browser check (Linux)"
echo "-------------------------------------"

found=""
for bin in google-chrome google-chrome-stable chromium chromium-browser chrome; do
    if command -v "$bin" >/dev/null 2>&1; then
        ver=$("$bin" --version 2>/dev/null || echo "$bin (version unknown)")
        # Extract the major version number when possible.
        major=$(echo "$ver" | grep -oE '[0-9]+' | head -1)
        if [ -n "$major" ] && [ "$major" -ge 113 ] 2>/dev/null; then
            pass "$ver (>= 113, WebGPU capable)"
        elif [ -n "$major" ]; then
            bad "$ver is too old (need Chrome/Chromium >= 113 for WebGPU)"
        else
            info "$ver (could not parse version; needs >= 113)"
        fi
        found="$found $bin"
    fi
done
[ -z "$found" ] && bad "no Chrome/Chromium found (need version 113+)"

if command -v firefox >/dev/null 2>&1; then
    info "$(firefox --version 2>/dev/null || echo firefox) — usable only with WebGPU enabled (see RUN-LINUX.md)"
fi

# GPU hint: a present /dev/dri usually means hardware acceleration is available.
if [ -e /dev/dri/card0 ] || [ -e /dev/dri/renderD128 ]; then
    pass "GPU render node present (/dev/dri) — hardware WebGPU likely"
else
    info "no /dev/dri node — the game may fall back to software rendering (slow)"
fi

# Headless smoke test: can Chrome actually start with WebGPU flags?
if [ -n "$found" ]; then
    bin=$(echo "$found" | awk '{print $1}')
    if timeout 15 "$bin" --headless=new --no-sandbox --dump-dom about:blank >/dev/null 2>&1; then
        pass "$bin launches headless"
    else
        bad "$bin failed a headless launch test"
    fi
fi

echo "-------------------------------------"
echo "Passed: $ok   Failed: $fail"
[ "$fail" -eq 0 ] && echo "RESULT: BROWSER READY" || echo "RESULT: INSTALL/UPDATE CHROME OR CHROMIUM (>= 113)"
exit "$fail"
