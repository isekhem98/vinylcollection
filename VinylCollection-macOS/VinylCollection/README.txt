Vinyl Collection Dashboard — macOS & Windows Setup
========================================

SECURITY FIRST
--------------
This app is now SECURE with enterprise-grade protections:

🔒 AUTHENTICATION: All data-modifying endpoints require login
🛡️  CSRF PROTECTION: Prevents cross-site request forgery attacks
🚦 RATE LIMITING: Protects against brute force and DoS attacks
🔐 HTTPS ENFORCEMENT: Forces secure connections (redirects HTTP to HTTPS)
📊 INPUT VALIDATION: Prevents SQL injection and XSS attacks
🔥 SECURITY HEADERS: Implements OWASP security headers
⚡ SECURE COOKIES: HTTPOnly, Secure, SameSite protection

Default login: admin / admin (CHANGE THIS IMMEDIATELY!)

QUICK START (recommended)
--------------------------
1. Make sure Python 3 is installed.
   Download from: https://www.python.org/downloads/
   Or install via package manager.

2. Double-click "start.command" (macOS), "start.bat" (Windows CMD), or run "start.ps1" (Windows PowerShell) to launch the app.
   - The first run installs dependencies and generates SSL certificate.
   - Your browser will open at https://127.0.0.1:5000
   - Note: SSL certificate is self-signed (browser may show warning)

3. That's it! Your vinyl.db and data.json files are created
   in the same folder on first run.

TERMINAL (alternative)
-----------------------
macOS: chmod +x start.sh && ./start.sh
Windows CMD: Run start.bat
Windows PowerShell: .\start.ps1
Or manually:
  pip3 install flask requests Flask-HTTPAuth cryptography
  python3 run.py

OPTIONS
-------
  Use a custom database path:
    python3 run.py --db /path/to/my.db

  Use custom SSL certificates:
    python3 run.py --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem

  Run on a different port (edit run.py and change port= argument)

SECURITY & HTTPS
----------------
🔐 AUTHENTICATION REQUIRED for all data operations
  - Login required to add/edit/delete vinyls, wants, config
  - Git updates require authentication
  - Feedback submission is public but rate-limited

🛡️ COMPREHENSIVE SECURITY FEATURES
  - CSRF protection on all forms
  - Rate limiting (50 requests/minute for most endpoints)
  - Input validation and sanitization
  - SQL injection prevention
  - XSS attack prevention
  - Secure session management
  - Security headers (CSP, HSTS, X-Frame-Options, etc.)

🔒 HTTPS ENCRYPTION
  - HTTPS enabled by default with auto-generated certificates
  - First run generates cert.pem and key.pem in the app folder
  - HTTP requests automatically redirect to HTTPS

ELIMINATING SSL WARNINGS (Recommended)
-------------------------------------
  Run the SSL setup script to get trusted certificates:
    Windows PowerShell: .\setup_ssl.ps1
  This installs mkcert and generates trusted certificates for localhost.
  No more browser warnings after setup!

  For production with your own domain, provide real SSL certificates:
    python run.py --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
  - Default admin credentials: username "admin", password "admin"
  - Change in webapp.py users dict for production.

SHARING YOUR COLLECTION
-----------------------
  - Click "Save" to export data.json
  - Send data.json to someone else; they click "Refresh" to load it

FEEDBACK & FEATURE REQUESTS
---------------------------
  - Click Settings → Feedback to submit ratings and suggestions
  - Feedback is stored LOCALLY in your database (vinyl.db)
  - Access feedback data: Settings → Config & API tokens (for developers)
  - Or query database: sqlite3 vinyl.db "SELECT * FROM feedback;"



REQUIREMENTS
------------
  Python 3.9 or newer
  Internet access for Discogs lookups

========================================
