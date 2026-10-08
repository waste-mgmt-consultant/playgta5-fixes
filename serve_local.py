"""Local mirror server: isolation headers, byte ranges, and engine batch I/O."""
import argparse, gzip, io, json, mimetypes, re, shutil, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs

ROOT = Path(__file__).resolve().parent / 'mirror' / 'playgta5.com'
USERDATA_BACKUP = Path(__file__).resolve().parent / 'save-backups' / 'live'
USERDATA_NAME = re.compile(r'SGTA5\d{4}(\.bak)?|pc_settings\.bin')  # basenames only: never a client-supplied path
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('text/javascript', '.js')
# Harmless engine warnings repeated thousands of times per session; crash reports are never filtered.
LOG_NOISE = re.compile(r"<ClothInstanc> \[Graphics\] grcBuffer|\[Parser\] (Array \S+ is a fixed size|Couldn't set the array size)|^0x[0-9a-f]+ - nosymbols\+0x[0-9a-f]+$")

def filter_log(text):
    if text.startswith('[page] CRASH'):
        return text
    return '\n'.join(line for line in text.split('\n') if not LOG_NOISE.search(line))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.byte_range = None
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Accept-Ranges', 'bytes')
        if not self.path.startswith('/data/'):
            # Revalidate code on every load (304 when unchanged); without this Chrome keeps running an edited script's old copy for hours.
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def send_head(self):
        if not self.headers.get('Range'):
            return super().send_head()
        path = Path(self.translate_path(self.path))
        if not path.is_file():
            self.send_error(404)
            return None
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers['Range'])
        if not match or not any(match.groups()):
            self.send_error(416)
            return None
        start = int(match[1]) if match[1] else max(0, size - int(match[2]))
        end = min(size - 1, int(match[2])) if match[1] and match[2] else size - 1
        if start >= size or end < start:
            self.send_response(416)
            self.send_header('Content-Range', 'bytes */%d' % size)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        self.byte_range = (start, end)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        source = path.open('rb')
        source.seek(start)
        return source

    def copyfile(self, source, outputfile):
        if self.byte_range is None:
            return super().copyfile(source, outputfile)
        remaining = self.byte_range[1] - self.byte_range[0] + 1
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

    def log_request(self, code='-', size='-'):
        pass  # no access lines; errors still print via log_error

    def do_POST(self):
        url = urlsplit(self.path)
        if url.path == '/log':
            # ?log=1 pages post engine, GPU worker and page log lines here.
            length = int(self.headers.get('Content-Length', '0'))
            text = filter_log(self.rfile.read(length).decode('utf-8', 'replace'))
            if text:
                print(text, flush=True)
            self.send_response(204)
            self.end_headers()
            return
        if url.path == '/userdata':
            # io_worker.js posts each settled savegame/settings file here as a copy outside the browser's IndexedDB.
            query = parse_qs(url.query)
            name, mtime = query.get('name', [''])[0], query.get('mtime', [''])[0]
            length = int(self.headers.get('Content-Length', '0'))
            if not USERDATA_NAME.fullmatch(name) or not mtime.isdigit() or not 0 < length <= 4 * 1024 * 1024:
                self.send_error(400)
                return
            USERDATA_BACKUP.mkdir(parents=True, exist_ok=True)
            (USERDATA_BACKUP / ('%s.%s' % (name, mtime))).write_bytes(self.rfile.read(length))
            print('[server] userdata backed up: save-backups/live/%s.%s (%d bytes)' % (name, mtime, length), flush=True)
            self.send_response(204)
            self.end_headers()
            return
        if url.path != '/data/batch':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        if length > 1024 * 1024:
            self.send_error(413)
            return
        try:
            runs = json.loads(self.rfile.read(length))
            if not isinstance(runs, list) or len(runs) > 1000:
                raise ValueError('invalid batch')
            selected = []
            data_root = (ROOT / 'data').resolve()
            for name, start, end in runs:
                file = (data_root / name).resolve()
                if not file.is_relative_to(data_root) or start < 0 or end < start:
                    raise ValueError('invalid file/range')
                selected.append((file, start, max(0, min(end + 1, file.stat().st_size) - start)))
            total = sum(n for _, _, n in selected)
            if total > 64 * 1024 * 1024:
                raise ValueError('batch exceeds 64 MiB')
            output = io.BytesIO()
            for file, start, n in selected:
                with file.open('rb') as source:
                    source.seek(start)
                    output.write(source.read(n))
            body = output.getvalue()
            compressed = parse_qs(url.query).get('gz') == ['1']
            if compressed:
                body = gzip.compress(body, compresslevel=1)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Run-Lengths', ','.join(str(n) for _, _, n in selected))
            if compressed:
                self.send_header('Content-Encoding', 'gzip')
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, TypeError, OSError) as exc:
            self.send_error(400, str(exc))

if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--port', type=int, default=8000)
    args.add_argument('--open', action='store_true', help='open the default browser after binding')
    options = args.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', options.port), Handler)
    address = 'http://localhost:%d/' % server.server_port
    print('Local mirror: %s (Ctrl+C to stop)' % address, flush=True)
    if options.open:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
