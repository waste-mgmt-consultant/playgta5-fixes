"""Build a portable standard-library Python runtime from the local Codex bundle.

Windows only: it copies python.exe, its DLLs and the standard library out of the
Windows Python that runs it. On Linux/macOS the system Python is used instead,
so this script refuses to run there (Launch-Local.sh / playgta5.sh call
`python3 serve_local.py` directly).
"""
import hashlib, json, shutil, sys, zipfile
from pathlib import Path

if sys.platform != 'win32':
    sys.exit('bundle_runtime.py is Windows-only: on Linux/macOS just use the system '
             'python3 (./playgta5.sh start). Nothing to bundle.')

ROOT = Path(__file__).resolve().parent
SOURCE = Path(sys.executable).parent
TARGET = ROOT / 'runtime'
TARGET.mkdir(exist_ok=True)
tag = 'python%d%d' % sys.version_info[:2]
for name in ['python.exe', 'python3.dll', tag + '.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt']:
    shutil.copyfile(SOURCE / name, TARGET / name)
shutil.copytree(SOURCE / 'DLLs', TARGET / 'DLLs', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pdb'))
with zipfile.ZipFile(TARGET / (tag + '.zip'), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted((SOURCE / 'Lib').rglob('*')):
        rel = path.relative_to(SOURCE / 'Lib')
        if path.is_file() and not any(part in {'site-packages', '__pycache__', 'test', 'tests'} for part in rel.parts) and path.suffix != '.pyc':
            archive.write(path, str(rel))
# An isolated path avoids depending on the user's Python install or site packages.
(TARGET / (tag + '._pth')).write_text(tag + '.zip\nDLLs\n.\n..\n', encoding='ascii')
records = []
for path in sorted(TARGET.rglob('*')):
    if path.is_file():
        records.append({'path': str(path.relative_to(ROOT)).replace('\\', '/'), 'bytes': path.stat().st_size,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(ROOT / 'snapshot/runtime-manifest.json').write_text(json.dumps({'python_version': sys.version,
    'source': str(SOURCE), 'scope': 'Python executable, DLLs and standard library; third-party packages excluded',
    'files': records}, indent=2), encoding='utf-8')
print('Portable runtime:', len(records), 'files;', sum(r['bytes'] for r in records), 'bytes')
