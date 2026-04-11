# Vinyl Collection Dashboard — Windows Launcher (PowerShell)

# Change to script directory
$scriptDir = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
Set-Location $scriptDir
Write-Host "Working directory: $(Get-Location)"

# Check for SSL certificates
$certFile = Join-Path $scriptDir "cert.pem"
$keyFile = Join-Path $scriptDir "key.pem"
if (-not (Test-Path $certFile) -or -not (Test-Path $keyFile)) {
    Write-Host "⚠️  SSL certificates not found." -ForegroundColor Yellow
    Write-Host "   Run .\setup_ssl.ps1 to generate trusted certificates and eliminate browser warnings." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Checking for Python..."
try {
    $version = py --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "Python found: $version"
} catch {
    Write-Host "Python (py command) is not available."
    Write-Host "Please ensure Python is installed and 'py' is in your PATH."
    Write-Host "Install from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Installing dependencies..."
try {
    py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Pip install failed"
    }
    Write-Host "Dependencies installed."
} catch {
    Write-Host "Failed to install dependencies: $_"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting the app..."
Write-Host "Access at: https://127.0.0.1:5000"
Write-Host "(Note: Accept SSL certificate warning or run .\setup_ssl.ps1 for trusted certificates)"
py run.py $args

Read-Host "Press Enter to exit"