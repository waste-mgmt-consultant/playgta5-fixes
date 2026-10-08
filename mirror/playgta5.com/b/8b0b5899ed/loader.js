// Worker that hosts the engine ("main runtime thread" of the Emscripten module). importScripts('game.js') runs the static constructors
// and main() here; the loop blocks this worker, which is fine (nothing else runs on it). game.js also runs in every pthread worker.
'use strict';
let started = false;
self.onmessage = (ev) => {
	if (started) return;
	started = true;
	const m = ev.data;
	// ?cores=N (debug): pretend to be a machine with N logical cores; the engine sizes its worker pools from it
	if (m.cores) Object.defineProperty(navigator, 'hardwareConcurrency', { value: m.cores });
	// The GPU worker must be up before the engine blocks this thread: Chrome fetches the script of a worker nested in a worker through
	// the parent's event loop. It idles until the engine sends its start message (wgpu_backend.cpp: wgpu_start_worker).
	const gq = new URLSearchParams();		// the GPU worker reads its options from its own URL
	if (m.slots) gq.set('slots', m.slots);
	if (m.syncPipelines) gq.set('syncpipelines', '1');
	if (m.remoteLog) gq.set('log', '1');		// ?log=1 on the page: its log lines go to the dev server (off by default)
	if (m.lowMemory) gq.set('low', '1');		// the low-memory profile: its own pipeline seed (wgpu_worker.js loadRecipes)
	if (m.noPack) gq.set('nopack', '1');		// ?nopack=1: shaders one by one instead of from the packs (diagnostics)
	if (m.shotRt) gq.set('shotrt', '1');		// ?shotrt=1 (with ?shot=N): every render target of one frame after the world is shown goes to the dev server (diagnosis)
	if (m.gpuLimits) gq.set('limits', m.gpuLimits);		// ?limits=name:value,...: a smaller device (diagnosis of weaker GPUs)
	const B = m.base || '';		// the page's URL prefix for everything it loads (index.html BASE): /b/<build> on the PHP host, empty otherwise
	const gpu = new Worker(B + '/wgpu_worker.js' + (gq.toString() ? '?' + gq : ''));
	const io = new Worker(B + '/io_worker.js?v=2');		// ?v: see index.html
	io.postMessage({ init: true, base: self.location.origin + '/data/', noStore: !!m.noStore, record: !!m.record, trace: !!m.trace, log: !!m.remoteLog, noHints: !!m.noHints, bootset: m.lowMemory ? 'bootset_low.json' : 'bootset.json' });		// starts the prefetch of the boot read set at once		// HTTP reads of all engine threads (platform/file/httpfs_wasm.cpp); same reason to create it up front
	let loaded = 0;
	io.onmessage = (e) => { if (e.data.loaded && ++loaded === 2) start(); };
	gpu.onmessage = (e) => {
		if (e.data.loaded && ++loaded === 2) start();
	};
	// An overloaded host answers 503/500/429 (2026-10-06): retried up to 8 times with growing, jittered waits (~20 s in all) instead of compiling an error page.
	const fetchWasm = async () => {
		for (let attempt = 0; ; attempt++) {
			let res = null, err = null;
			try { res = await fetch(B + '/game.wasm'); } catch (e) { err = e; }
			if (res && res.ok) return res;
			if (attempt >= 7) { if (res) throw new Error('HTTP ' + res.status + ' for game.wasm'); throw err; }
			bc0.postMessage({ label: 'The server is busy, retrying (' + (attempt + 1) + ')' });
			await new Promise((r) => setTimeout(r, Math.min(5000, 300 * 2 ** attempt) * (0.5 + Math.random())));
		}
	};
	const bc0 = new BroadcastChannel('game-progress');
	const start = () => {
		const bc = new BroadcastChannel('game-progress');
		self.Module = {
			// Download game.wasm ourselves to report progress (0-20 %); emscripten hands the compiled module on to the pthread workers.
			instantiateWasm: (imports, done) => {
				// Streaming compilation: the module compiles while it downloads (no compile wait after the download, no 2 x 63 MB buffer copy, and Chrome can cache the
				// compiled code of a fetched response for the next visit). Progress is counted on a clone of the response. Any failure falls back to download-then-compile.
				const buffered = async () => {
					const res = await fetchWasm();
					const total = +(res.headers.get('X-Uncompressed-Length') || res.headers.get('Content-Length')) || 0;
					const reader = res.body.getReader(), chunks = [];
					let got = 0;
					for (;;) {
						const { done: end, value } = await reader.read();
						if (end) break;
						chunks.push(value);
						got += value.length;
						bc.postMessage({ pct: total ? 20 * got / total : 0, label: 'Downloading the engine (' + (got / 1048576 | 0) + ' MB)' });
					}
					const bytes = new Uint8Array(got);
					let o = 0;
					for (const c of chunks) { bytes.set(c, o); o += c.length; }
					bc.postMessage({ pct: 20, label: 'Compiling the engine' });
					return WebAssembly.instantiate(bytes, imports);
				};
				const streaming = async () => {
					const res = await fetchWasm();
					const total = +(res.headers.get('X-Uncompressed-Length') || res.headers.get('Content-Length')) || 0;		// the body is decoded while it is read: count decoded bytes
					const counter = res.clone().body.getReader();
					(async () => {
						let got = 0;
						for (;;) {
							const { done: end, value } = await counter.read();
							if (end) break;
							got += value.length;
							bc.postMessage({ pct: total ? 20 * got / total : 0, label: 'Downloading and compiling the engine (' + (got / 1048576 | 0) + ' MB)' });
						}
						bc.postMessage({ pct: 20, label: 'Compiling the engine' });
					})().catch(() => {});
					return WebAssembly.instantiateStreaming(res, imports);
				};
				(async () => {
					let r;
					try { r = await streaming(); }
					catch (e) { console.warn('streaming instantiation failed (' + e + '): downloading first'); r = await buffered(); }
					bc.postMessage({ pct: 22, label: 'Starting the engine' });
					done(r.instance, r.module);
				})().catch((e) => { bc.postMessage({ error: 'engine download failed: ' + e }); });
				return {};
			},
			canvas: m.canvas,
			arguments: m.args,
			wgpuWorker: gpu,
			ioWorker: io,
			fullConsole: !!m.fullConsole,		// ?console=1: every engine line in the browser console (default: errors, warnings, the port's lines)
			remoteLog: !!m.remoteLog,		// ?log=1: every engine line to the dev server's log (prejs.js; default: none)
			wgpuShaderUrl: B + '/shaders',
			wgpuShotEvery: m.shotEvery,
			keepThreads: m.keepThreads|0,		// bit mask of engine thread groups that are NOT skipped (1 replay, 2 net, 4 bink), see ipc_wasm.cpp
			mainScriptUrlOrBlob: B + '/game.js' + ((m.fullConsole || m.remoteLog) ? '?' + [m.fullConsole ? 'console=1' : '', m.remoteLog ? 'log=1' : ''].filter(Boolean).join('&') : ''),		// pthreads read both from it, and take game.wasm's folder from it
			locateFile: (p) => B + '/' + p,
			onExit: (code) => { console.error('EXIT ' + code); self.__log('EXIT ' + code); self.__logFlush(); if (code) self.__crash('exit', 'EXIT ' + code); },
			onAbort: (what) => { console.error('ABORT ' + what); self.__log('ABORT ' + what); self.__logFlush(); self.__crash('abort', 'ABORT ' + what); },
			// Savegames and settings kept in IndexedDB by io_worker.js (platform/file/userdata_wasm.cpp sends them): put them back into the in-memory /userdata before the engine looks at it. The run
			// dependency holds main() until they are in (or 8 s, so a broken IndexedDB cannot keep the game from starting). Only /userdata/ paths are accepted.
			preRun: [() => {
				if (typeof FS === 'undefined' || typeof addRunDependency !== 'function' || typeof indexedDB === 'undefined') return;
				addRunDependency('userdata');
				let finished = false;
				const finish = (note) => { if (finished) return; finished = true; self.__log('[loader] userdata: ' + note); self.__logFlush(); removeRunDependency('userdata'); };
				setTimeout(() => finish('timed out'), 8000);
				try {
					const r = indexedDB.open('gta5-userdata', 1);
					r.onupgradeneeded = () => r.result.createObjectStore('files');
					r.onerror = () => finish('IndexedDB unavailable: ' + r.error);
					r.onsuccess = () => {
						let n = 0, bytes = 0;
						try {
							// finish() can start main(), which never returns to this worker's event loop. Called from inside a request callback, the
							// transaction never commits and its lock blocks every later write by io_worker.js. So finish only once it has completed.
							const db = r.result, t = db.transaction('files', 'readonly');
							t.oncomplete = () => { db.close(); finish('restored ' + n + ' file(s), ' + bytes + ' bytes'); };
							t.onabort = () => { db.close(); finish('read aborted: ' + t.error); };
							const req = t.objectStore('files').openCursor();		// a failed request aborts the transaction: onabort reports it
							req.onsuccess = () => {
								const c = req.result;
								if (!c) return;
								const path = String(c.key);
								try {
									if (path.startsWith('/userdata/') && c.value && c.value.data) {
										FS.mkdirTree(path.slice(0, path.lastIndexOf('/')));
										FS.writeFile(path, c.value.data);
										FS.utime(path, c.value.mtime, c.value.mtime);
										n++; bytes += c.value.data.length;
									}
								} catch (e) { self.__log('[loader] userdata: ' + path + ' not restored: ' + e); }
								c.continue();
							};
						} catch (e) { finish('read failed: ' + e); }
					};
				} catch (e) { finish('failed: ' + e); }
			}],
		};
		// __log/__logFlush come from prejs.js, which only exists once game.js is loaded: note the start line in the console.
		console.log('loader: starting engine: ' + m.args.join(' ') + ' (cores ' + m.cores + ')');
		importScripts(B + '/game.js');
	};
	gpu.onerror = (e) => console.error('gpu worker failed to load: ' + e.message);
};
