<#
.SYNOPSIS
  Start the SIH26162 stack for local development, each service in its own window.

.DESCRIPTION
  One click: double-click run.bat (or run this script). On the first run it
  creates the venv and installs backend + web deps automatically; after that it
  just starts everything and opens the dashboard in your browser.

  Launches:
    - FastAPI backend  (uvicorn --reload)  -> http://localhost:8000
    - Vite web app     (npm run dev)       -> http://localhost:5173 (auto-opens)
    - Expo mobile app  (npx expo start)    -> optional, with -Mobile
    - Celery worker+beat (6-hourly FIRMS ingest) -> optional, with -Worker
                                                   (needs REDIS_URL in .env)

  Requires a filled-in .env at the repo root (copy from .env.example).

.EXAMPLE
  .\dev.ps1                 # one-click: install-if-needed, start, open browser
.EXAMPLE
  .\dev.ps1 -Install        # force a fresh pip/npm install, then start
.EXAMPLE
  .\dev.ps1 -Seed           # load the demo snapshot first (fresh/empty DB only)
.EXAMPLE
  .\dev.ps1 -Mobile         # also start the Expo dev server
.EXAMPLE
  .\dev.ps1 -Worker         # also start the Celery scheduled-ingest worker
.EXAMPLE
  .\dev.ps1 -NoWeb          # backend only
#>
[CmdletBinding()]
param(
  [switch]$Install,
  [switch]$Mobile,
  [switch]$Worker,
  [switch]$NoWeb,
  [switch]$Seed
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }

# --- pre-flight -------------------------------------------------------------
if (-not (Test-Path (Join-Path $root ".env"))) {
  Write-Warning "No .env at repo root. Copy .env.example to .env and fill it in first."
}

# # prefer a project virtualenv if one exists, else system python
# $py = "python"
# foreach ($cand in @("backend\.venv\Scripts\python.exe", ".venv\Scripts\python.exe")) {
#   $p = Join-Path $root $cand
#   if (Test-Path $p) { $py = $p; break }
# --- Python environment -----------------------------------------------------

$venv = Join-Path $root "backend\.venv"
$py = Join-Path $venv "Scripts\python.exe"

$freshVenv = $false
if (-not (Test-Path $py)) {
  Write-Host "`n== creating Python 3.12 virtual environment =="

  & py -3.12 -m venv $venv

  if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3.12 is required but was not found. Install Python 3.12 first."
    exit 1
  }
  $freshVenv = $true
}

Write-Host "python  : $py"
Write-Host "version : $(& $py --version)"
Write-Host "repo    : $root"

function Start-Service([string]$Title, [string]$WorkDir, [string]$Command) {
  Write-Host "start   : $Title"
  $inner = "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location '$WorkDir'; $Command"
  Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $inner) | Out-Null
}

# --- install (auto on first run; force with -Install) ----------------------
if ($Install -or $freshVenv) {
  Write-Host "`n== installing backend deps =="
  & $py -m pip install -r (Join-Path $root "backend\requirements.txt")
}

if ($Install -or -not (Test-Path (Join-Path $root "web\node_modules"))) {
  Write-Host "`n== installing web deps =="
  Push-Location (Join-Path $root "web"); npm install; Pop-Location
}

if ($Mobile -and ($Install -or -not (Test-Path (Join-Path $root "mobile\node_modules")))) {
  Write-Host "`n== installing mobile deps =="
  Push-Location (Join-Path $root "mobile"); npm install; Pop-Location
}

# --- seed the demo DB (opt-in; needed only on a fresh/empty database) -------
if ($Seed) {
  Write-Host "`n== loading demo snapshot into the database =="
  Push-Location (Join-Path $root "backend")
  try { & $py scripts\demo_snapshot.py load } catch { Write-Warning "seed failed: $_" }
  Pop-Location
}

# --- launch -------------------------------------------------------------
Start-Service "firedetect-api" (Join-Path $root "backend") "& '$py' -m uvicorn app.main:app --reload --port 8000"

if (-not $NoWeb) {
  Start-Service "firedetect-web" (Join-Path $root "web") "npm run dev"
  # give Vite a moment to bind, then open the dashboard (no extra hidden powershell.exe spawn)
  Start-Sleep 8
  Start-Process 'http://localhost:5173'
}

if ($Mobile) {
  Start-Service "firedetect-mobile" (Join-Path $root "mobile") "npx expo start"
}

if ($Worker) {
  $celery = "& '$py' -m celery -A app.workers.celery_app worker --beat --pool=solo " +
            "--loglevel=info --without-gossip --without-mingle --without-heartbeat"
  Start-Service "firedetect-worker" (Join-Path $root "backend") $celery
}

Write-Host ""
Write-Host "up:"
Write-Host "  api    -> http://localhost:8000/health   (Swagger: http://localhost:8000/docs)"
if (-not $NoWeb) { Write-Host "  web    -> http://localhost:5173" }
if ($Mobile) { Write-Host "  expo   -> scan the QR in the firedetect-mobile window" }
if ($Worker) { Write-Host "  worker -> ingests FIRMS now + every 6h (firedetect-worker window)" }
Write-Host ""
Write-Host "each service runs in its own window - close the window (or Ctrl+C in it) to stop that service."
