"""Check inventory sizes, engine signature, shader samples, and local HTTP I/O."""
import gzip, hashlib, json, threading
from pathlib import Path
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from serve_local import Handler, ROOT

BASE = Path(__file__).resolve().parent

# Files deliberately changed by the playgta5-fixes patches. The scrape manifest
# (snapshot/manifest-sha256.json) records the ORIGINAL site bytes, so these four
# must DIFFER from it — that difference is the proof the fixes are applied.
# game.wasm.orig must still match: it is the untouched backup.
FIXED = {'/index.html', '/b/8b0b5899ed/loader.js', '/b/8b0b5899ed/io_worker.js',
         '/b/8b0b5899ed/game.wasm'}
# Repo-root reference copies of the fixed scripts (LF line endings; the served
# mirror copies use CRLF). Maps manifest path -> repo file.
FIXED_REFS = {'/b/8b0b5899ed/loader.js': 'loader.js',
              '/b/8b0b5899ed/io_worker.js': 'io_worker.js'}

def norm(content):
    return content.replace(b'\r\n', b'\n')

def main():
    inventory = json.loads((BASE / 'snapshot/manifest-sha256.json').read_text())
    known = {r['path']: r for r in inventory}
    missing = []
    wrong_size = []
    fixed_files = []
    for rec in inventory:
        path = ROOT / rec['path'].lstrip('/')
        if not path.is_file():
            missing.append(rec['path'])
        elif rec['path'] in FIXED:
            # Size and hash differ by design; verify the fix is really present.
            actual = path.read_bytes()
            assert hashlib.sha256(actual).hexdigest() != rec['sha256'], \
                'fix missing (matches original): ' + rec['path']
            ref = FIXED_REFS.get(rec['path'])
            if ref is not None:
                assert norm(actual) == norm((BASE / ref).read_bytes()), \
                    'served copy out of sync with repo ' + ref
            fixed_files.append({'path': rec['path'], 'manifest_bytes': rec['bytes'],
                                'fixed_bytes': len(actual)})
        elif path.stat().st_size != rec['bytes']:
            wrong_size.append(rec['path'])
    manifest = json.loads((BASE / 'data-manifest.json').read_text())
    uncovered = [f[0] for f in manifest['files'] if '/data/' + f[0] not in known]
    discrepancies = [r for r in inventory if r.get('manifest_bytes') is not None and r['bytes'] != r['manifest_bytes']]
    wasm = ROOT / 'b/8b0b5899ed/game.wasm'
    with wasm.open('rb') as source:
        assert source.read(8) == b'\x00asm\x01\x00\x00\x00', 'invalid WASM signature'
    # The untouched backup must still match the scraped original byte for byte.
    assert hashlib.sha256((ROOT / 'b/8b0b5899ed/game.wasm.orig').read_bytes()).hexdigest() == \
        known['/b/8b0b5899ed/game.wasm']['sha256'], 'game.wasm.orig is not the untouched original'
    # Hash small runtime/control files and one derived shader, not a second 21 GB sweep.
    # FIXED entries are checked in the inventory loop above, so they are excluded here.
    sample = [r for r in inventory if r['path'] in ['/index.html', '/data/manifest.json',
        '/b/8b0b5899ed/game.js', '/b/8b0b5899ed/loader.js', '/b/8b0b5899ed/io_worker.js',
        '/b/8b0b5899ed/wgpu_worker.js', '/b/8b0b5899ed/shaders/index.json'] and r['path'] not in FIXED]
    sample += [r for r in inventory if r.get('derived_from')][:2]
    for rec in sample:
        assert hashlib.sha256((ROOT / rec['path'].lstrip('/')).read_bytes()).hexdigest() == rec['sha256']
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    origin = 'http://127.0.0.1:%d' % httpd.server_port
    try:
        with urlopen(origin + '/') as response:
            assert response.headers['Cross-Origin-Opener-Policy'] == 'same-origin'
            assert response.headers['Cross-Origin-Embedder-Policy'] == 'require-corp'
            assert response.read() == (ROOT / 'index.html').read_bytes()
        with urlopen(Request(origin + '/b/8b0b5899ed/game.wasm', headers={'Range': 'bytes=0-7'})) as response:
            assert response.status == 206 and response.read() == b'\x00asm\x01\x00\x00\x00'
        name = 'common/data/Clouds.xml'
        original = (ROOT / 'data' / name).read_bytes()
        body = json.dumps([[name, 0, 63], [name, 100, 131]]).encode()
        for query in ['', '?gz=1']:
            with urlopen(Request(origin + '/data/batch' + query, data=body)) as response:
                result = response.read()
                if query:
                    result = gzip.decompress(result)
                assert result == original[:64] + original[100:132]
                assert response.headers['X-Run-Lengths'] == '64,32'
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join()
    report = {'inventory_files': len(inventory), 'inventory_bytes': sum(r['bytes'] for r in inventory),
        'data_manifest_files': len(manifest['files']), 'missing': missing, 'wrong_size': wrong_size,
        'fixed_files': fixed_files,
        'uncovered_data_files': uncovered, 'source_size_discrepancies': discrepancies,
        'sample_sha256_passed': len(sample), 'wasm_signature': 'passed',
        'wasm_backup_match': 'passed',
        'http_tests': ['isolation headers', 'index bytes', 'WASM range', 'plain batch', 'gzip batch'],
        'hash_scope': 'All downloaded files hashed during transfer; selected small files rehashed afterward; the four fix files are verified to differ from the scrape manifest (fix applied) and the wasm backup to match it.',
        'browser_game_execution': 'not tested'}
    (BASE / 'snapshot/verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    assert not (missing or wrong_size or uncovered), 'snapshot incomplete'

if __name__ == '__main__':
    main()
