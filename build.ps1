# Build script for AgentCore Lambda package
param(
    [string]$OutputZip = "agentcore-runtime.zip",
    [string]$Platform = "manylinux2014_aarch64",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$PackageDir = Join-Path $RootDir "package"
$RequirementsFile = Join-Path $RootDir "requirements.txt"
$SrcDir = Join-Path $RootDir "src"
$UtilsDir = Join-Path $RootDir "utils"
$OutputPath = Join-Path $RootDir $OutputZip

Write-Host "Building AgentCore runtime package..." -ForegroundColor Cyan

# Clean previous build
if ($Clean -or (Test-Path $PackageDir)) {
    Write-Host "Cleaning previous build..." -ForegroundColor Yellow
    if (Test-Path $PackageDir) {
        Remove-Item -Recurse -Force $PackageDir
    }
    if (Test-Path $OutputPath) {
        Remove-Item -Force $OutputPath
    }
}

# Create package directory
Write-Host "Creating package directory..." -ForegroundColor Green
New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null

# Install dependencies
Write-Host "Installing dependencies for platform: $Platform..." -ForegroundColor Green
pip install -r $RequirementsFile -t $PackageDir --platform $Platform --only-binary=:all:

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies"
    exit 1
}

# Copy application code (preserving src directory structure)
Write-Host "Copying source code..." -ForegroundColor Green
Copy-Item -Path $SrcDir -Destination $PackageDir -Recurse -Force

# Copy utils module
Write-Host "Copying utils module..." -ForegroundColor Green
Copy-Item -Path $UtilsDir -Destination $PackageDir -Recurse -Force

# Remove files that shouldn't be in the deployment package
$ExcludeFiles = @("Dockerfile", ".env", ".env.example")
foreach ($file in $ExcludeFiles) {
    $filePath = Join-Path (Join-Path $PackageDir "src") $file
    if (Test-Path $filePath) {
        Remove-Item -Force $filePath
        Write-Host "  Excluded: $file" -ForegroundColor Yellow
    }
}

# Remove __pycache__ directories
Get-ChildItem -Path $PackageDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Write-Host "  Excluded: __pycache__ directories" -ForegroundColor Yellow

# Create ZIP
Write-Host "Creating ZIP archive: $OutputZip..." -ForegroundColor Green
if (Test-Path $OutputPath) {
    Remove-Item -Force $OutputPath
}

Compress-Archive -Path "$PackageDir\*" -DestinationPath $OutputPath -CompressionLevel Optimal

if (Test-Path $OutputPath) {
    $zipSize = (Get-Item $OutputPath).Length / 1MB
    Write-Host "Build complete: $OutputZip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Cyan
} else {
    Write-Error "Failed to create ZIP archive"
    exit 1
}
