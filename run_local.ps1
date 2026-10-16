# run_local.ps1 - Levanta jAImes COMPLETO en local (sin AWS).
#   Backend FastAPI (uvicorn) + Frontend PWA (Vite) + SQLite sembrada E-1.
#   Uso:  powershell -ExecutionPolicy Bypass -File run_local.ps1

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$zip = Join-Path $backend "dataset_e1_publico.zip"
$db = Join-Path $backend "jaimes_local.db"
# Ruta ABSOLUTA a la BD (independiente del cwd del proceso).
$dbUrl = "sqlite:///" + ($db -replace "\\","/")

$env:USE_MOCKS = "true"
$env:DATABASE_URL = $dbUrl
$env:DATASET_ZIP_PATH = $zip

if ((-not (Test-Path $db)) -or ((Get-Item $db).Length -eq 0)) {
  Write-Host "[jAImes] Sembrando SQLite con el dataset oficial E-1..."
  Push-Location $backend; & $py -m app.repositories.seed.seed; Pop-Location
} else { Write-Host "[jAImes] BD ya sembrada." }

Write-Host "[jAImes] Backend -> puerto 8000"
$beCmd = "/c set USE_MOCKS=true&& set DATABASE_URL=$dbUrl&& ""$py"" -m uvicorn app.main:app --port 8000"
Start-Process cmd.exe -ArgumentList $beCmd -WorkingDirectory $backend

if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Push-Location $frontend; npm install; Pop-Location }
Write-Host "[jAImes] Frontend -> puerto 5173"
Start-Process cmd.exe -ArgumentList "/c npm run dev" -WorkingDirectory $frontend

Start-Sleep -Seconds 4
Write-Host "[jAImes] Listo. App (puerto 5173) y API/Swagger /docs (puerto 8000)."
Write-Host "[jAImes] Mi sala: jardin JAR-0009, sala SG-A (19 ninos)."
