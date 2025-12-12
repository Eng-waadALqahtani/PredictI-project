# Quick Check Script for Deployment Readiness
Write-Host "Checking deployment files..." -ForegroundColor Cyan
Write-Host ""

$allOk = $true

# Check essential files
$files = @(
    "requirements.txt",
    "render.yaml",
    ".gitignore",
    "create-deployment-zip.ps1",
    "backend\main.py",
    "backend\engine.py",
    "backend\models.py",
    "backend\storage.py",
    "frontend\js\events.js",
    "ml\models\isoforest_absher.pkl"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "[OK] $file" -ForegroundColor Green
    } else {
        Write-Host "[MISSING] $file" -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "All files are ready! You can run: .\create-deployment-zip.ps1" -ForegroundColor Green
} else {
    Write-Host "Some files are missing. Please check above." -ForegroundColor Yellow
}

