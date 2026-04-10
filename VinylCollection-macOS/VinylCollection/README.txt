Vinyl Collection Dashboard — macOS Setup
========================================

QUICK START (recommended)
--------------------------
1. Make sure Python 3 is installed.
   Download from: https://www.python.org/downloads/
   Or install via Homebrew: brew install python

2. Double-click "start.command" to launch the app.
   - The first run installs Flask & Requests automatically.
   - Your browser will open at http://127.0.0.1:5000

3. That's it! Your vinyl.db and data.json files are created
   in the same folder on first run.

TERMINAL (alternative)
-----------------------
  chmod +x start.sh
  ./start.sh

Or manually:
  pip3 install flask requests
  python3 run.py

OPTIONS
-------
  Use a custom database path:
    python3 run.py --db /path/to/my.db

  Run on a different port (default 5000):
    Edit run.py and change the port= argument in main()

SHARING YOUR COLLECTION
-----------------------
  - Click "Save" to export data.json
  - Send data.json to someone else; they click "Refresh" to load it

REQUIREMENTS
------------
  Python 3.9 or newer
  Internet access for Discogs lookups

========================================
