# ============================================================================
# PredictAI - Create Deployment ZIP Script
# ============================================================================
# This script creates a clean ZIP file ready for Render deployment
# Excludes: venv, __pycache__, .ipynb_checkpoints, and other unnecessary files
# ============================================================================

Write-Host "Creating deployment ZIP for PredictAI..." -ForegroundColor Cyan
Write-Host ""

# Get the script directory (project root)
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$zipName = "hakathoon-deployment.zip"
$zipPath = Join-Path $projectRoot $zipName

# Remove existing ZIP if it exists
if (Test-Path $zipPath) {
    Write-Host "Removing existing ZIP file..." -ForegroundColor Yellow
    Remove-Item $zipPath -Force
}

# Files and folders to include
$includeItems = @(
    "backend\main.py",
    "backend\engine.py",
    "backend\models.py",
    "backend\storage.py",
    "backend\ml",
    "frontend",
    "ml",
    "requirements.txt",
    "render.yaml",
    ".gitignore"
)

# Add all .md files
$mdFiles = Get-ChildItem -Path $projectRoot -Filter "*.md" -File
foreach ($mdFile in $mdFiles) {
    $includeItems += $mdFile.Name
}

Write-Host "Including files:" -ForegroundColor Green
foreach ($item in $includeItems) {
    $fullPath = Join-Path $projectRoot $item
    if (Test-Path $fullPath) {
        Write-Host "   [OK] $item" -ForegroundColor Gray
    } else {
        Write-Host "   [WARN] $item (not found)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Creating ZIP file..." -ForegroundColor Cyan

# Create temporary directory for clean files
$tempDir = Join-Path $env:TEMP "hakathoon-deploy-$(Get-Random)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    # Copy files to temp directory
    foreach ($item in $includeItems) {
        $sourcePath = Join-Path $projectRoot $item
        $destPath = Join-Path $tempDir $item
        
        if (Test-Path $sourcePath) {
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            
            if (Test-Path $sourcePath -PathType Container) {
                # Copy directory, excluding unwanted subdirectories
                $excludeDirs = @("venv", "__pycache__", ".ipynb_checkpoints", "node_modules", ".git")
                Get-ChildItem -Path $sourcePath -Recurse | Where-Object {
                    $relativePath = $_.FullName.Substring($sourcePath.Length + 1)
                    $pathParts = $relativePath.Split([IO.Path]::DirectorySeparatorChar)
                    -not ($excludeDirs | Where-Object { $pathParts -contains $_ })
                } | ForEach-Object {
                    $relativePath = $_.FullName.Substring($sourcePath.Length + 1)
                    $targetPath = Join-Path $destPath $relativePath
                    $targetDir = Split-Path $targetPath -Parent
                    if (-not (Test-Path $targetDir)) {
                        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                    }
                    Copy-Item $_.FullName -Destination $targetPath -Force
                }
            } else {
                Copy-Item $sourcePath -Destination $destPath -Force
            }
        }
    }
    
    # Create ZIP from temp directory
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force
    
    # Get ZIP size
    $zipSize = (Get-Item $zipPath).Length / 1MB
    $zipSizeFormatted = "{0:N2}" -f $zipSize
    
    Write-Host ""
    Write-Host "[SUCCESS] ZIP file created successfully!" -ForegroundColor Green
    Write-Host "   Location: $zipPath" -ForegroundColor Cyan
    Write-Host "   Size: $zipSizeFormatted MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Upload this ZIP to GitHub (or extract and upload files)" -ForegroundColor White
    Write-Host "   2. Connect GitHub repository to Render" -ForegroundColor White
    Write-Host "   3. Render will auto-detect render.yaml and deploy" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Error creating ZIP: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clean up temp directory
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
}

Write-Host "Done!" -ForegroundColor Green

