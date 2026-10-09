# Running playgta5-fixes on Linux

This guide explains how to run the archived GTA V web client (playgta5.com) locally
on Linux, with the community fixes for saves, shop menus, memory crashes and a
money hotkey.

Everything runs in your **browser** (WebAssembly + WebGPU). Python is only used as
a small local file server. No Windows required.

---

## 1. Requirements

| Item | Minimum |
|------|---------|
| OS | Any modern Linux (tested layout: Linux Mint / Ubuntu) |
| Python | 3.11 or newer (standard library only) |
| Browser | Chrome / Chromium / Edge 113+ (WebGPU + shared-memory wasm) |
| Disk | ~21 GB for the game data |
| GPU | WebGPU-capable (recent Intel/AMD/NVIDIA) |

Check your Python:

```bash
python3 --version    # should print 3.12.x or similar
```

> Firefox can work if WebGPU is enabled, but Chrome/Chromium is recommended.

---

## 2. Folder layout

Your checkout should look like this after setup:

```
playgta5-fixes/
├── mirror/playgta5.com/            # game data (~21 GB) — added below
│   ├── index.html                  # FIXED copy (kept)
│   ├── data/                       # RPF archives + manifest
│   └── b/8b0b5899ed/
│       ├── game.wasm               # patched by patch_shop_menus.py
│       ├── game.js
│       ├── io_worker.js            # FIXED copy (kept)
│       ├── loader.js               # FIXED copy (kept)
│       ├── wgpu_worker.js
│       └── shaders/
├── patch_shop_menus.py             # wasm patcher
├── serve_local.py                  # local HTTP server
├── Launch-Local.sh                 # Linux launcher (this guide)
├── patch.sh                        # Linux patch helper
└── README.md
```

The three **FIXED** files live inside `mirror/`. Never overwrite them when adding
your own copy of the data.

---

## 3. Add the game data (`mirror` folder)

The repo ships **only scripts** — no Rockstar files. You need the ~19.7 GB `mirror`
folder (from the community, e.g. Telegram `https://t.me/playgta5regen`) or the
`GTA5Webport.zip` bundle.

### 3a. If you have `GTA5Webport.zip`

Extract only the mirror data (the ZIP stores it under `playgta5-offline/mirror/`):

```bash
cd /home/mint/Desktop/playgta5-fixes
unzip -o GTA5Webport.zip 'playgta5-offline/mirror/*' -d _staging
# Move data into place (rename is instant — no extra disk use):
rm -rf mirror
mv _staging/playgta5-offline/mirror mirror
rm -rf _staging
# Restore the FIXED files that the ZIP would otherwise overwrite:
git checkout -- mirror
```

### 3b. If you have a plain `mirror` folder

```bash
cd /home/mint/Desktop/playgta5-fixes
cp -rn /path/to/your/mirror/playgta5.com ./mirror/   # -n = never overwrite fixed files
# then, to be safe:
git checkout -- mirror
```

Verify the data landed:

```bash
ls mirror/playgta5.com/data/manifest.json
du -sh mirror/          # expect ~20 GB
```

---

## 4. Apply the fixes (patch `game.wasm`)

```bash
cd /home/mint/Desktop/playgta5-fixes
./patch.sh
# or: python3 patch_shop_menus.py
```

Expected output:

```
game.wasm patched: 63201802 -> 63202084 bytes, sha256 3ea63e8d...
```

- The first run saves the untouched file as `game.wasm.orig`.
- Running it again is safe.
- To **undo**: `cp mirror/playgta5.com/b/8b0b5899ed/game.wasm.orig mirror/playgta5.com/b/8b0b5899ed/game.wasm`

---

## 5. Start the game

```bash
cd /home/mint/Desktop/playgta5-fixes
chmod +x *.sh                # first time only
./playgta5.sh doctor         # full health check: install + browser + status
./patch.sh                   # apply the game.wasm fixes (if verify says UNPATCHED)
```

Or with `make`:

```bash
make doctor
make patch
```

The script:
- starts the server on `http://localhost:8000/`
- opens your browser
- streams logs to the terminal (`last-session.log`)
- press **Ctrl+C** to stop

Then, **first load only**, do a hard reload to bypass the browser cache:

```
Ctrl+Shift+R
```

### Manual alternative

```bash
python3 serve_local.py --port 8000        # then open http://localhost:8000/
python3 serve_local.py --port 8000 --open # also tries to open the browser
```

Custom port:

```bash
PORT=8080 ./Launch-Local.sh
```

---

## 6. Controls

| Input | Action |
|-------|--------|
| **Enter** | Story Mode |
| **Space**, then **5** | Sandbox Mode on the GTA V map |
| **Space**, then **6** | Sandbox Mode on the "GTA VI" map (`env_test`) |
| **=** | Toggle FPS counter |
| **-** (key right of `0`) | +$999,999 to the current character |

Direct map URLs:
- Sandbox GTA V: `http://localhost:8000/?mode=sandbox`
- Sandbox env_test: `http://localhost:8000/?mode=sandbox&map=env_test`

---

## 7. Saves

Saves are stored in two places:

1. **Browser IndexedDB** (`gta5-userdata`) — restored automatically on load.
2. **On disk** — `save-backups/live/SGTA500xx.<timestamp>` written by the server.

To verify saving works: save in game, wait a few seconds, then:

```bash
ls -la save-backups/live/
```

If the browser ever loses your saves, copy them back from `save-backups/live/`.

---

## 8. What was fixed

| Problem | Fix |
|---------|-----|
| Saves vanished after reload | `loader.js` starts the engine only after the restore transaction commits; `io_worker.js` times out hanging writes and mirrors every save to the server; `serve_local.py` keeps `save-backups/live/`. |
| Shop menus never opened | `patch_shop_menus.py` makes missing texture dictionaries and scaleform movies report "loaded" instead of blocking the menu. |
| Crash after long sessions ("Invalid fixup…") | Streaming heap is capped at 1 GB (4 × 256 MB) so the engine evicts old models instead of hitting the 3 GB wasm limit. Side effect: occasional texture pop-in. Change `GROW_HEAP_LIMIT` in `patch_shop_menus.py` to adjust. |
| Bonus: easy money | Press **`-`** for +$999,999. |

---

## 9. Troubleshooting

**"Port 8000 already in use"**
Another server is running. Stop it (`./playgta5.sh stop`), or use `PORT=8080 ./Launch-Local.sh`.

**Black screen / nothing loads**
- Confirm you did the patch (`./patch.sh`) and a hard reload (`Ctrl+Shift+R`).
- Check the terminal for errors; `last-session.log` has the full session log.
- Make sure `mirror/playgta5.com/data/manifest.json` exists.

**"WebGPU not available" / shared memory error**
Use Chrome/Chromium 113+. For LAN (non-localhost) URLs you must enable
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` with the exact origin.

**Textures pop in / objects disappear**
That is the intended side effect of the 1 GB heap cap (crash fix). Raise
`GROW_HEAP_LIMIT` in `patch_shop_menus.py` and re-run `./patch.sh` if your machine
has RAM to spare (it may crash again on very long sessions).

**Saves not appearing on disk**
Check `save-backups/live/` and the terminal log. The server logs every backup.

**Performance tips**
- `?low=1` (used by the launcher) lowers graphics and core count for stability.
- `?cores=N` to force a core count; `?nopack=1` to load shaders one by one.
- Use `= ` in game to watch FPS.

---

## 10. Files created by this Linux setup

| File | Purpose |
|------|---------|
| `Launch-Local.sh` | Linux launcher (server + browser + logs) |
| `Launch-LAN.sh` | Serve to other devices on your network |
| `patch.sh` | Runs `patch_shop_menus.py` with checks |
| `verify_linux.sh` | Checks the whole setup is complete/correct |
| `check_browser.sh` | Checks for a WebGPU-capable browser |
| `playgta5.sh` | Master command: `start lan patch verify browser doctor status stop shortcut setup help` |
| `install-shortcut.sh` | (Re)installs the desktop shortcut |
| `setup_linux.sh` | One-shot setup (extract + merge + patch) |
| `finish_linux.sh` | Verifies setup and deletes the ZIP to reclaim space |
| `PlayGTA5.desktop` | Desktop / app-menu shortcut |
| `RUN-LINUX.md` | This document |
| `last-session.log` / `previous-session.log` | Session logs |
| `save-backups/live/` | On-disk copies of saves |

### Play from the desktop

Double-click **Play GTA5 (Local)** on your Desktop (or find it in the app menu).

The first time, Linux Mint/Cinnamon may ask to trust the launcher — click
**"Allow Launching"**. To (re)install or repair the shortcut:

```bash
./install-shortcut.sh
```

### Health checks

```bash
./playgta5.sh verify    # 12-point install check (fast)
./playgta5.sh browser   # Chrome/Chromium + GPU check (fast)
./playgta5.sh doctor    # everything above + full snapshot check:
                        # all 12,482 files + live server tests
                        # (isolation headers, ranges, batch I/O)
```

`verify_snapshot.py` is fix-aware: the four patched files (`index.html`,
`loader.js`, `io_worker.js`, `game.wasm`) are verified to *differ* from the
original scrape (fix applied), the untouched `game.wasm.orig` to *match* it,
and the served `loader.js`/`io_worker.js` to equal the repo's reference copies.
The repo-root `loader.js`/`io_worker.js` are kept in sync with the fixed
served versions (LF line endings; served copies use CRLF — equivalent to browsers).

### Serve to another device on your LAN

```bash
./Launch-LAN.sh          # listens on 0.0.0.0:8080 and prints the URLs
```

On the client device, open the printed `http://<server-ip>:8080/` URL. Because
WebGPU needs a secure context, whitelist that exact origin once in the client
browser at `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, then
restart the browser. (Not needed for `localhost`.)


---

## Credits & disclaimer

The original client and site are by the playgta5.com authors. Scrape by Sebas
Furbastian. This repo contains only scripts and the web client code — no Rockstar
files. The `mirror` data is copyrighted by Rockstar Games; you must supply your own.
