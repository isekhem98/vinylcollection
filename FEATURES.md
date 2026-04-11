# Vinyl Collection Dashboard — Feature Documentation

## Overview
This document explains all the new features added to the Vinyl Collection Dashboard and provides comprehensive information for using and deploying the application.

---

## 1. Feedback System

### Where is Feedback Sent/Stored?
Feedback is **stored locally in the SQLite database** in the `feedback` table. It is **NOT** sent to any external server. The data remains on your machine unless you explicitly export it or share it.

**Database Location:**
- Windows/Mac: `vinyl.db` (same folder as the app)
- Database Table: `feedback` with columns:
  - `id` (integer, primary key)
  - `rating` (integer, 1-5)
  - `suggestions` (text)
  - `submitted_date` (date, auto-filled)

**How to Access Feedback:**
1. Open the app and go to Settings → Feedback
2. Submit a rating (1-5) and optional suggestions
3. Feedback is immediately saved to the local database
4. To view feedback programmatically:
   ```bash
   sqlite3 vinyl.db "SELECT * FROM feedback;"
   ```
5. Feedback is included in JSON exports via "Save" button and can be shared if desired

---

## 2. Authentication & Security

### Default Credentials
- Username: `admin`
- Password: `admin`

⚠️ **IMPORTANT:** Change these credentials in production!

### Where to Change Credentials
Edit `webapp.py`, line ~47:
```python
users = {
    "admin": generate_password_hash("your_new_password")
}
```

### Protected Endpoints
- `/api/git-update` - Requires basic HTTP authentication

### How to Use Authentication
When making API calls to protected endpoints, include the Authorization header:
```bash
curl -u admin:admin -X POST http://localhost:5000/api/git-update
```

---

## 3. Git Integration

### Auto-Update from GitHub
The app includes a `/api/git-update` endpoint that runs `git pull` to update from your repository.

**Requirements:**
- Git must be installed and in PATH
- Repository must be initialized (`.git` folder present)
- Basic authentication required (see #2)

**Usage:**
```bash
# Using curl
curl -u admin:admin -X POST http://localhost:5000/api/git-update

# Using PowerShell
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
Invoke-WebRequest -Uri "http://localhost:5000/api/git-update" `
  -Method POST `
  -Headers @{"Authorization"="Basic $auth"}
```

**Deployment Note:** For hosting on GitHub Pages or similar platforms, this endpoint allows automated updates without manual intervention.

---

## 4. HTTPS/SSL Support (Production)

### Enabling HTTPS
Generate or obtain SSL certificates, then start the app with:
```bash
python run.py --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
```

### Self-Signed Certificate (Testing)
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Start app with HTTPS
python run.py --ssl-cert cert.pem --ssl-key key.pem
```

### Docker Deployment with HTTPS
The included `Dockerfile` allows deployment on cloud platforms like:
- Heroku (with Procfile)
- Railway
- AWS ECS
- Google Cloud Run
- DigitalOcean App Platform

Example Heroku deployment with SSL:
```bash
git push heroku main
```

---

## 5. Windows & Cross-Platform Support

### Windows Launchers
- **Command Prompt:** `start.bat` (auto-detects Python)
- **PowerShell:** `start.ps1` (recommended for PATH issues)

### macOS Launchers
- **Terminal:** `start.command` (executable)
- **Terminal:** `start.sh` (bash script)

### CLI Arguments
```bash
# Custom database path
python run.py --db /custom/path/vinyl.db

# HTTPS support
python run.py --ssl-cert cert.pem --ssl-key key.pem

# Both
python run.py --db /custom/path/vinyl.db --ssl-cert cert.pem --ssl-key key.pem
```

---

## 6. API Reference

### Feedback Endpoints

**Submit Feedback**
```
POST /api/feedback
Content-Type: application/json

{
  "rating": 5,
  "suggestions": "Great app!"
}
```

Response:
```json
{"ok": true}
```

**Get All Feedback**
```
GET /api/feedback
```

Response:
```json
[
  {
    "id": 1,
    "rating": 5,
    "suggestions": "Great app!",
    "submitted_date": "2026-04-11"
  }
]
```

### Git Update
```
POST /api/git-update
Authorization: Basic {base64(username:password)}
```

Response on success:
```json
{"ok": true, "output": "Already up to date"}
```

---

## 7. Running Comprehensive Tests

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
python test_vinyl_collection.py
```

### Test Coverage
The test suite includes:

1. **Database Tests** (`TestDatabase`)
   - Feedback table creation
   - Feedback CRUD operations
   - Config operations
   - Vinyl record CRUD
   - Wantlist operations

2. **API Tests** (`TestWebAppAPI`)
   - Index and feedback routes
   - Feedback submission and retrieval
   - Vinyl CRUD via API
   - Config API
   - Stats endpoint
   - Git update authentication

3. **Authentication Tests** (`TestAuthentication`)
   - Default user verification
   - Password verification
   - HTTP auth header generation

4. **Data Export Tests** (`TestDataExport`)
   - JSON export functionality
   - JSON import functionality

### Expected Output
```
test_add_feedback_api ... ok
test_add_feedback_invalid_rating ... ok
test_add_vinyl_api ... ok
test_auth_header_format ... ok
test_auth_verify_correct_password ... ok
test_config_api ... ok
test_default_user_exists ... ok
test_export_to_json ... ok
test_feedback_route ... ok
test_feedback_table_exists ... ok
test_get_all_feedback ... ok
test_get_feedback_api ... ok
test_git_update_requires_auth ... ok
test_index_route ... ok
test_stats_api ... ok
test_vinyl_crud ... ok
test_wantlist_operations ... ok

======================================================================
TEST SUMMARY
======================================================================
Tests run: 17
Successes: 17
Failures: 0
Errors: 0
======================================================================
```

---

## 8. Deployment Checklist

### Before Production
- [ ] Change default admin password
- [ ] Enable HTTPS (obtain SSL certificates)
- [ ] Test all endpoints with new credentials
- [ ] Run `test_vinyl_collection.py` and fix any failures
- [ ] Configure firewall/security groups
- [ ] Set up database backups
- [ ] Review log output for errors

### Heroku Deployment
```bash
# Create Procfile
echo "web: python run.py" > Procfile

# Deploy
git add Procfile
git commit -m "Add Procfile for Heroku"
git push heroku main

# View logs
heroku logs --tail
```

### Docker Deployment
```bash
# Build image
docker build -t vinyl-collection .

# Run container
docker run -p 5000:5000 vinyl-collection

# With volume for persistent data
docker run -p 5000:5000 -v $(pwd)/data:/app/data vinyl-collection
```

---

## 9. Troubleshooting

### Problem: "requirements.txt not found"
**Solution:** Ensure you're running the launcher script from the app directory:
- Windows PowerShell: `.\start.ps1` (from the app folder)
- macOS Terminal: `./start.sh` (from the app folder)

### Problem: "Python not found"
**Solution:** 
- Try `start.ps1` instead of `start.bat`
- Verify Python PATH: `python --version` or `py --version`
- Reinstall Python from https://www.python.org/downloads/

### Problem: "Port 5000 already in use"
**Solution:** Change port via code or use:
```bash
python run.py  # then manually edit run.py to change port
```

### Problem: "SSL certificate error"
**Solution:**
- Use `--ssl-cert` and `--ssl-key` arguments with valid paths
- Or remove SSL args to run over HTTP (local development only)

---

## 10. Security Best Practices

1. **Always use HTTPS in production**
2. **Change default admin credentials immediately**
3. **Don't share SSL private keys**
4. **Regularly backup your `vinyl.db` file**
5. **Review feedback data for sensitive information**
6. **Use strong passwords for authentication**
7. **Keep Python and dependencies updated**
8. **Run tests before deploying to production**

---

## Summary

| Feature | Status | Storage | Access |
|---------|--------|---------|--------|
| Feedback | ✓ Active | Local SQLite DB | Via `/api/feedback` |
| Authentication | ✓ Active | Hardcoded in code | Basic HTTP Auth |
| Git Updates | ✓ Active | Git repository | `/api/git-update` |
| HTTPS | ✓ Supported | SSL certs | `--ssl-cert` argument |
| Cross-Platform | ✓ Supported | N/A | start.ps1 / start.sh |
| Tests | ✓ Comprehensive | 17 test cases | `test_vinyl_collection.py` |

