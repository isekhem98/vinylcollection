# Production SSL Setup for Vinyl Collection App
# This script sets up FREE Let's Encrypt SSL certificates

param(
    [Parameter(Mandatory=$true)]
    [string]$DomainName,

    [Parameter(Mandatory=$false)]
    [string]$Email = "admin@$DomainName"
)

Write-Host "🔐 Vinyl Collection - Production SSL Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Domain: $DomainName" -ForegroundColor White
Write-Host "Email: $Email" -ForegroundColor White
Write-Host ""

# Check if running as administrator (required for SSL certificate installation)
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator for SSL certificate installation." -ForegroundColor Red
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if domain is accessible
Write-Host "🔍 Checking if domain $DomainName is accessible..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://$DomainName" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "✅ Domain is accessible" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Domain $DomainName is not accessible via HTTP." -ForegroundColor Yellow
    Write-Host "   Make sure:" -ForegroundColor White
    Write-Host "   - Your domain DNS points to this server" -ForegroundColor White
    Write-Host "   - Port 80 is open and accessible" -ForegroundColor White
    Write-Host "   - No other web server is running on port 80" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}

# Stop any existing web server on port 80
Write-Host "🛑 Checking for services on port 80..." -ForegroundColor Yellow
$port80Process = Get-NetTCPConnection -LocalPort 80 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($port80Process) {
    Write-Host "⚠️  Port 80 is in use. This is required for SSL certificate verification." -ForegroundColor Yellow
    Write-Host "   Please stop any web servers running on port 80" -ForegroundColor Yellow
    exit 1
}

# Get Certbot path
$certbotPath = "C:\Users\Ionut\AppData\Local\Programs\Python\Python314\Scripts\certbot.exe"
if (-not (Test-Path $certbotPath)) {
    Write-Host "❌ Certbot not found at $certbotPath" -ForegroundColor Red
    Write-Host "   Please run: py -m pip install certbot" -ForegroundColor Yellow
    exit 1
}

# Generate SSL certificate
Write-Host "🔐 Generating SSL certificate for $DomainName..." -ForegroundColor Yellow
Write-Host "   This will:" -ForegroundColor White
Write-Host "   - Start a temporary web server on port 80" -ForegroundColor White
Write-Host "   - Verify domain ownership with Let's Encrypt" -ForegroundColor White
Write-Host "   - Generate trusted SSL certificates" -ForegroundColor White
Write-Host ""

$certbotArgs = @(
    "certonly",
    "--standalone",
    "--agree-tos",
    "--email", $Email,
    "-d", $DomainName,
    "--cert-name", $DomainName
)

try {
    & $certbotPath @certbotArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "" -ForegroundColor White
        Write-Host "🎉 SUCCESS! SSL certificate generated for $DomainName" -ForegroundColor Green
    } else {
        Write-Host "❌ Certificate generation failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error running Certbot: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Check if certificates were created
$certDir = "C:\Certbot\live\$DomainName"
if (-not (Test-Path $certDir)) {
    # Try alternative location
    $certDir = "$env:APPDATA\Certbot\live\$DomainName"
}

if (-not (Test-Path $certDir)) {
    Write-Host "❌ Certificate directory not found" -ForegroundColor Red
    exit 1
}

$certFile = Join-Path $certDir "fullchain.pem"
$keyFile = Join-Path $certDir "privkey.pem"

if ((Test-Path $certFile) -and (Test-Path $keyFile)) {
    Write-Host "📄 Certificate files created:" -ForegroundColor Green
    Write-Host "   📄 $certFile" -ForegroundColor White
    Write-Host "   🔑 $keyFile" -ForegroundColor White
    Write-Host ""

    # Copy certificates to app directory for convenience
    Write-Host "📋 Copying certificates to app directory..." -ForegroundColor Yellow
    Copy-Item $certFile ".\cert.pem" -Force
    Copy-Item $keyFile ".\key.pem" -Force
    Write-Host "✅ Certificates copied to current directory" -ForegroundColor Green
    Write-Host ""

    # Create production startup script
    $prodScript = @"
# Production startup script for $DomainName
Write-Host "🚀 Starting Vinyl Collection App (Production)" -ForegroundColor Green
Write-Host "Domain: https://$DomainName" -ForegroundColor White
Write-Host ""

# Check for production SSL certificates
`$certFile = "$certFile"
`$keyFile = "$keyFile"

if ((Test-Path `$certFile) -and (Test-Path `$keyFile)) {
    Write-Host "✅ SSL certificates found" -ForegroundColor Green
    py run.py --ssl-cert `$certFile --ssl-key `$keyFile
} else {
    Write-Host "❌ SSL certificates not found" -ForegroundColor Red
    Write-Host "Run .\setup_ssl_production.ps1 -DomainName $DomainName to generate certificates" -ForegroundColor Yellow
}
"@

    $prodScript | Out-File -FilePath "start_production.ps1" -Encoding UTF8
    Write-Host "📝 Created production startup script: start_production.ps1" -ForegroundColor Green
    Write-Host ""

    # Setup auto-renewal
    Write-Host "🔄 Setting up automatic certificate renewal..." -ForegroundColor Yellow
    $taskName = "VinylCollection_SSL_Renewal"

    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "✅ Renewal task already exists" -ForegroundColor Green
    } else {
        # Create renewal task (runs daily at 2 AM)
        $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$certbotPath`" renew --quiet"
        $trigger = New-ScheduledTaskTrigger -Daily -At 2am
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType InteractiveToken

        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Automatic SSL certificate renewal for Vinyl Collection app"

        Write-Host "✅ Auto-renewal task created (runs daily at 2 AM)" -ForegroundColor Green
    }

    Write-Host "" -ForegroundColor White
    Write-Host "🎊 PRODUCTION SSL SETUP COMPLETE!" -ForegroundColor Green
    Write-Host "" -ForegroundColor White
    Write-Host "🚀 Start your app in production mode:" -ForegroundColor Cyan
    Write-Host "   .\start_production.ps1" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "🌐 Your app will be available at:" -ForegroundColor Cyan
    Write-Host "   https://$DomainName" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "📋 Certificate Details:" -ForegroundColor Yellow
    Write-Host "   - FREE Let's Encrypt SSL" -ForegroundColor White
    Write-Host "   - Auto-renews every 90 days" -ForegroundColor White
    Write-Host "   - Trusted by all browsers" -ForegroundColor White
    Write-Host "   - Production security level" -ForegroundColor White

} else {
    Write-Host "❌ Certificate files not found after generation" -ForegroundColor Red
    exit 1
}