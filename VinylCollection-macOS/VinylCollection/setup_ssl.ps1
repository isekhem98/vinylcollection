# Automated SSL Setup for Vinyl Collection
# This script installs mkcert and generates trusted SSL certificates

Write-Host "🔐 Vinyl Collection - SSL Certificate Setup" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check if mkcert is already installed
$mkcertInstalled = $false
try {
    $null = Get-Command mkcert -ErrorAction Stop
    $mkcertInstalled = $true
    Write-Host "✅ mkcert is already installed" -ForegroundColor Green
} catch {
    Write-Host "📦 mkcert not found. Installing..." -ForegroundColor Yellow
}

if (-not $mkcertInstalled) {
    # Try Chocolatey first (most common on Windows)
    try {
        $null = Get-Command choco -ErrorAction Stop
        Write-Host "📦 Installing mkcert via Chocolatey..." -ForegroundColor Yellow
        choco install mkcert -y
        $mkcertInstalled = $true
    } catch {
        Write-Host "❌ Chocolatey not found. Trying manual installation..." -ForegroundColor Red
    }
}

if (-not $mkcertInstalled) {
    # Manual installation
    Write-Host "📦 Downloading mkcert manually..." -ForegroundColor Yellow

    # Create temp directory
    $tempDir = Join-Path $env:TEMP "mkcert_install"
    if (-not (Test-Path $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir | Out-Null
    }

    # Download latest mkcert release
    $apiUrl = "https://api.github.com/repos/FiloSottile/mkcert/releases/latest"
    try {
        $release = Invoke-RestMethod -Uri $apiUrl
        $asset = $release.assets | Where-Object { $_.name -like "*windows-amd64.exe" } | Select-Object -First 1

        if ($asset) {
            $downloadUrl = $asset.browser_download_url
            $exePath = Join-Path $tempDir "mkcert.exe"

            Write-Host "⬇️  Downloading mkcert..." -ForegroundColor Yellow
            Invoke-WebRequest -Uri $downloadUrl -OutFile $exePath

            # Move to a directory in PATH
            $installDir = "$env:USERPROFILE\bin"
            if (-not (Test-Path $installDir)) {
                New-Item -ItemType Directory -Path $installDir | Out-Null
            }

            Copy-Item $exePath (Join-Path $installDir "mkcert.exe")
            $env:PATH += ";$installDir"

            Write-Host "✅ mkcert installed to $installDir" -ForegroundColor Green
            $mkcertInstalled = $true
        } else {
            throw "Could not find Windows AMD64 release"
        }
    } catch {
        Write-Host "❌ Failed to download mkcert: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Please install mkcert manually from: https://github.com/FiloSottile/mkcert/releases" -ForegroundColor Red
        exit 1
    }
}

# Install CA (Certificate Authority)
Write-Host "🔐 Installing local Certificate Authority..." -ForegroundColor Yellow
try {
    & mkcert -install
    Write-Host "✅ Certificate Authority installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install CA: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "You may need to run this script as Administrator" -ForegroundColor Red
    exit 1
}

# Generate certificates
Write-Host "📄 Generating SSL certificates for localhost..." -ForegroundColor Yellow
try {
    & mkcert -cert-file cert.pem -key-file key.pem localhost 127.0.0.1
    Write-Host "✅ SSL certificates generated" -ForegroundColor Green
    Write-Host "   📄 cert.pem (certificate)" -ForegroundColor White
    Write-Host "   🔑 key.pem (private key)" -ForegroundColor White
} catch {
    Write-Host "❌ Failed to generate certificates: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Verify certificates exist
if ((Test-Path "cert.pem") -and (Test-Path "key.pem")) {
    Write-Host "" -ForegroundColor White
    Write-Host "🎉 SUCCESS! Trusted SSL certificates created." -ForegroundColor Green
    Write-Host "   Your browser will no longer show SSL warnings." -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "🚀 Start your app with:" -ForegroundColor Cyan
    Write-Host "   .\start.ps1" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "📖 Visit: https://127.0.0.1:5000" -ForegroundColor Cyan
} else {
    Write-Host "❌ Certificate files not found after generation" -ForegroundColor Red
    exit 1
}