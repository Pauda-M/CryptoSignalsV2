echo off
REM
REM init-system.ps1 - Initialize CryptoTrader V2 on Windows
REM Works on Windows 10+ with PowerShell 5.1+
REM
REM Usage:
REM   powershell -ExecutionPolicy Bypass -File ops\scripts\init-system.ps1
REM

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CryptoTrader V2 - System Initialization" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check OS
$OS = "windows"
Write-Host "✓ Detected OS: $OS" -ForegroundColor Green

# Check Node.js
	try {
    $nodeVersion = node -v
    Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
		}, 
	catch {
    Write-Host "❌ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 	}

# Check Python
	try {
    $pythonVersion = python --version
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
	} catch {
    Write-Host "❌ Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 
	}

Write-Host ""
Write-Host "========== Installing Dependencies ==========" -ForegroundColor Yellow

# Create .env from .env.example if not exists
	if (-not (Test-Path ".env")) {
    Write-Host "📋 Creating .env from .env.example..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Edit .env with your database connection string" -ForegroundColor Yellow
	}

# Install root dependencies
Write-Host "📦 Installing root dependencies..." -ForegroundColor Cyan
	if (Test-Path "package.json") {
    npm install
	}

# Install service dependencies
Write-Host "📦 Installing service dependencies..." -ForegroundColor Cyan
Get-ChildItem -Path "services" -Directory | ForEach-Object {
    $packagePath = Join-Path $_.FullName "package.json"
    if (Test-Path $packagePath) {
        Write-Host "  Installing $($_.Name)..." -ForegroundColor Gray
        Push-Location $_.FullName
        npm install
        Pop-Location
    }
}

# Install dashboard dependencies
Write-Host "📦 Installing dashboard dependencies..." -ForegroundColor Cyan
Get-ChildItem -Path "dashboards" -Directory | ForEach-Object {
    $packagePath = Join-Path $_.FullName "package.json"
    if (Test-Path $packagePath) {
        Write-Host "  Installing $($_.Name)..." -ForegroundColor Gray
        Push-Location $_.FullName
        npm install
        Pop-Location
    }
		}

# Create Python virtual environment
Write-Host "📦 Creating Python virtual environment..." -ForegroundColor Cyan
	if (-not (Test-Path "venv")) {
    python -m venv venv
}

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Cyan
$reqPath = "ml\requirements.txt"
	if (Test-Path $reqPath) {
    & "venv\Scripts\python.exe" -m pip install -r $reqPath
	}

# Create necessary directories
Write-Host "📁 Creating data directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "ml\models" | Out-Null
New-Item -ItemType Directory -Force -Path "backups" | Out-Null

Write-Host ""
Write-Host "========== System Initialized ==========" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env with your database connection string" -ForegroundColor Gray
Write-Host "  2. Run: powershell -ExecutionPolicy Bypass -File ops\scripts\db-init.ps1" -ForegroundColor Gray
Write-Host "  3. Run: powershell -ExecutionPolicy Bypass -File ops\scripts\start-all.ps1" -ForegroundColor Gray
Write-Host ""
