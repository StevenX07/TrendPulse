$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "No se encontró el entorno virtual en .venv\Scripts\python.exe"
    exit 1
}

Write-Host "Iniciando backend local TrendPulse (http://127.0.0.1:8000)..." -ForegroundColor Cyan
$BackendJob = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $Root `
    -PassThru `
    -WindowStyle Hidden

try {
    Write-Host "Iniciando interfaz web TrendPulse (http://localhost:5173)..." -ForegroundColor Green
    Push-Location (Join-Path $Root "frontend")
    npm run dev
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
    if ($BackendJob -and -not $BackendJob.HasExited) {
        Write-Host "Deteniendo backend local..." -ForegroundColor Yellow
        Stop-Process -Id $BackendJob.Id -Force -ErrorAction SilentlyContinue
    }
}
