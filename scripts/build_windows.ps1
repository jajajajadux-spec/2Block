param()
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
    & python -m PyInstaller --noconfirm --clean --onefile --windowed --name 2Block-Setup --paths $projectRoot scripts/client.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    Write-Host 'Built dist/2Block-Setup.exe. Restart or reload the portal to see its download link.'
} finally {
    Pop-Location
}
