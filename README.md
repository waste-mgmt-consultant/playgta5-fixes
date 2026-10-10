# playgta5 fixes

The playgta5.com web client, scraped before the site went down, plus fixes for the problems that made it hard to actually play:

- **Saves disappear** after a reload.
- **Shop menus never open** (Los Santos Customs, clothes, barbers, ...).
- **The game crashes after a long session** ("Invalid fixup ... is neither virtual nor physical").
- **Missions freeze when a TV movie stops** (Michael's TV in Complications).
- Bonus: a **money hotkey**.

No Rockstar files are in this repo. You need your own copy of the `mirror` folder (about 19.7 GB).

## What was fixed

### Saves get lost
Saving looked fine, but after a reload the save was gone. The loader restored saves from IndexedDB and started the engine inside the read callback. The engine never returns, so that read transaction never finished and kept its lock. Every later save write waited behind it forever, without an error.

- `loader.js`: the engine starts only after the restore transaction has completed.
- `io_worker.js`: a write that hangs times out and is logged instead of waiting silently. Every save is also sent to the local server.
- `serve_local.py`: keeps a copy of every save on disk in `save-backups/live/` (`SGTA500xx.<time>`). If the browser ever loses your saves, they are there. The server also tells the browser not to cache the scripts, so fixes like these take effect without clearing the cache.

### Shop menus never open
The data set has no `update.rpf`, so the MP/NG menu assets (`MPShopSale.ytd`, the `COLOUR_SWITCHER` movies) are missing. The shop scripts wait for them forever. `patch_shop_menus.py` patches `game.wasm` so a missing texture dictionary or scaleform movie reports "loaded" instead of blocking the menu.

### Crash after playing for a while
The streaming resource heap grew by 256 MB every time it filled up and never evicted anything. In a long session the game died while loading a map piece. (The wasm memory starts at 3 GB but can grow to 16 GB; `game.js` sets `maximum: 262144n` pages.) The patch caps that heap at 1.5 GB (6 x 256 MB), so the game unloads the least used models instead of growing. A side effect can be a little texture pop-in. Change `GROW_HEAP_LIMIT` in `patch_shop_menus.py` if you want a different cap. A 1 GB cap (4) was too small for Complications: the heap filled to 1018/1024 MB and missions stalled with streaming requests that could never be placed.

### Freeze when a TV movie stops
This build has no Bink, so the `AsyncBink` thread never starts and no movie ever reports loaded. `CMovieMgr::Delete` (and six other inlined copies of `CMovie::WaitTillLoaded`) slept until it did, so the main thread hung in "Movie Manager" for good, for example when Michael's TV switches off in Complications. The patch makes those waits take their existing skip path. TV screens stay blank as before.

### Money hotkey
Press **`-`** (the key right of `0`) in game: the current character gets **+$999,999**. Once per press, in both Story Mode and Sandbox Mode. The game never sees that key.

## How to apply

1. **Get the files.** `git clone` this repo or download the ZIP.

2. **Add your `mirror` folder** to the repo folder. The repo already contains three fixed files inside `mirror/` (`index.html`, `b/8b0b5899ed/io_worker.js`, `b/8b0b5899ed/loader.js`). Your mirror must not overwrite them:
   - Copying with Explorer/Finder: when it asks about existing files, choose **skip**.
   - Or copy everything and then run `git checkout -- mirror` to put the fixed files back.

   <p align="center">
     <img src="media/Screenshot 2026-10-07 172216.png" alt="mirror folder size">
   </p>

3. **Patch `game.wasm`** from the repo folder:
   - Windows: `runtime\python.exe patch_shop_menus.py`
   - macOS / Linux: `python3 patch_shop_menus.py`

   It should print `game.wasm patched: 63201802 -> 63202084 bytes, sha256 e548c603...`. The first run keeps the untouched file as `game.wasm.orig`. Running it again is safe. It refuses to touch a `game.wasm` that is not the expected build, so nothing breaks if your mirror is different.

   To undo: copy `game.wasm.orig` over `game.wasm` (in `mirror/playgta5.com/b/8b0b5899ed/`).

4. **Start the game:**
   - Windows: `Launch-Local.cmd`
   - macOS: `Launch-Local.command` (it refuses to start a second server if one is already running)

   Then open `http://localhost:8000/`. The first time after updating, do one hard reload (Ctrl+Shift+R / Cmd+Shift+R).

5. **Check that saves work** (optional). Save in game and wait a few seconds. A file should appear in `save-backups/live/`.

## Title screen
- **Enter**: Story Mode.
- **Space**, then **5**: Sandbox Mode on the GTA V map. Space alone only opens the map choice; the game waits there until you press 5.
- **Space**, then **6**: Sandbox Mode on the "GTA VI map" (`env_test`), if your mirror has it.
- **`=`** toggles the FPS counter.

## Credits
The original client and site are by the playgta5.com authors. The scrape and the first repo are by Sebas Furbastian (Telegram @SebasKitten, X @Sebas_Kitten). Community: https://t.me/playgta5regen

## Disclaimer
This repo has only scripts and the web client code. It does not include `game.wasm`, game data or any other Rockstar Games file, and it will not. Don't ask for the mirror folder.
