$ErrorActionPreference = 'Stop'
# Portable launcher: prefer the bundled Windows runtime, then any python on PATH.
# (The old version hardcoded one author's C:\Users\sebas\... path.)
$root = $PSScriptRoot
$candidates = @(
    (Join-Path $root 'runtime\python.exe'),
    'python',
    'python3',
    'py'
)
$pythonExe = $null
foreach ($c in $candidates) {
    try {
        $cmd = Get-Command $c -ErrorAction Stop
        if ($cmd) { $pythonExe = $cmd.Source; break }
    } catch { }
}
if (-not $pythonExe) {
    throw 'No Python found. Install Python 3.11+ or extract the bundled runtime/.'
}
& $pythonExe (Join-Path $root 'serve_local.py')
