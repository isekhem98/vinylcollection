# SSL Setup Script for Vinyl Collection
# This script installs mkcert and generates trusted SSL certificates

param(
    [switch]$Force
)

Write-Host "🔒 Vinyl Collection - SSL Certificate Setup" -ForegroundColor Cyan
Write-Host "=" * 50

$AppDir = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$CertFile = Join-Path $AppDir "cert.pem"
$KeyFile = Join-Path $AppDir "key.pem"

# Check if certificates already exist
if ((Test-Path $CertFile) -and (Test-Path $KeyFile) -and -not $Force) {
    Write-Host "✓ SSL certificates already exist at:" -ForegroundColor Green
    Write-Host "  Certificate: $CertFile"
    Write-Host "  Key: $KeyFile"
    Write-Host ""
    Write-Host "Use -Force to regenerate certificates."
    exit 0
}

# Check if mkcert is installed
$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if (-not $mkcert) {
    Write-Host "📥 mkcert not found. Installing..." -ForegroundColor Yellow

    # Try Chocolatey first
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "Installing via Chocolatey..."
        & choco install mkcert -y
    } else {
        # Manual download
        Write-Host "Chocolatey not found. Downloading mkcert manually..." -ForegroundColor Yellow
        Write-Host ""

        $url = "https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-windows-amd64.exe"
        $tempFile = Join-Path $env:TEMP "mkcert.exe"

        try {
            Write-Host "Downloading from: $url"
            Invoke-WebRequest -Uri $url -OutFile $tempFile -UseBasicParsing

            # Copy to app directory
            Copy-Item $tempFile (Join-Path $AppDir "mkcert.exe")
            Write-Host "✓ mkcert downloaded to: $(Join-Path $AppDir "mkcert.exe")" -ForegroundColor Green

            # Clean up temp file
            Remove-Item $tempFile -ErrorAction SilentlyContinue
        } catch {
            Write-Host "❌ Failed to download mkcert. Please download manually from:" -ForegroundColor Red
            Write-Host "   https://github.com/FiloSottile/mkcert/releases/latest" -ForegroundColor Red
            Write-Host "   Look for: mkcert-v1.4.4-windows-amd64.exe" -ForegroundColor Red
            Write-Host "   Place it in: $AppDir" -ForegroundColor Red
            exit 1
        }
    }
}

# Install CA (Certificate Authority)
Write-Host ""
Write-Host "🔐 Installing local Certificate Authority..." -ForegroundColor Yellow
try {
    if (Test-Path (Join-Path $AppDir "mkcert.exe")) {
        & (Join-Path $AppDir "mkcert.exe") -install
    } else {
        & mkcert -install
    }

    if ($LASTEXITCODE -ne 0) {
        throw "mkcert install failed"
    }
    Write-Host "✓ Certificate Authority installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install Certificate Authority" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Generate certificates
Write-Host ""
Write-Host "📄 Generating SSL certificates for localhost..." -ForegroundColor Yellow
try {
    if (Test-Path (Join-Path $AppDir "mkcert.exe")) {
        & (Join-Path $AppDir "mkcert.exe") -cert-file $CertFile -key-file $KeyFile localhost 127.0.0.1
    } else {
        & mkcert -cert-file $CertFile -key-file $KeyFile localhost 127.0.0.1
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Certificate generation failed"
    }

    Write-Host "✓ SSL certificates generated:" -ForegroundColor Green
    Write-Host "  Certificate: $CertFile" -ForegroundColor Green
    Write-Host "  Key: $KeyFile" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to generate certificates" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Verify certificates
Write-Host ""
Write-Host "🔍 Verifying certificates..." -ForegroundColor Yellow
if ((Test-Path $CertFile) -and (Test-Path $KeyFile)) {
    $certSize = (Get-Item $CertFile).Length
    $keySize = (Get-Item $KeyFile).Length

    Write-Host "✓ Certificate file size: $certSize bytes" -ForegroundColor Green
    Write-Host "✓ Key file size: $keySize bytes" -ForegroundColor Green

    # Test certificate with OpenSSL if available
    if (Get-Command openssl -ErrorAction SilentlyContinue) {
        Write-Host ""
        Write-Host "🔒 Certificate details:" -ForegroundColor Cyan
        & openssl x509 -in $CertFile -subject -issuer -dates -noout 2>$null
    }
} else {
    Write-Host "❌ Certificate files not found after generation" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 SSL setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start the app: .\start.ps1" -ForegroundColor White
Write-Host "2. Open: https://127.0.0.1:5000" -ForegroundColor White
Write-Host "3. No more SSL warnings! 🎊" -ForegroundColor White
Write-Host ""
Write-Host "Note: The certificate is trusted locally and will work in all browsers." -ForegroundColor Yellow