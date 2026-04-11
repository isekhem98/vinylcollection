# Feedback System - Complete Guide

## Overview

The Vinyl Collection Dashboard includes a user feedback system that allows users to rate their experience and suggest new features. All feedback is stored **completely locally** in your database and never sent anywhere.

## How Users Submit Feedback

1. Open the app (https://127.0.0.1:5000)
2. Click **Settings** (gear icon) in the top-right
3. Select **Feedback**
4. Select a rating (1-5 stars)
5. Optionally add suggestions or comments
6. Click **Submit Feedback**

## Where is Feedback Stored?

### Storage Location
**Database:** `vinyl.db` (in your app folder)
**Table:** `feedback`
**Location:** Stored entirely on your local machine - NOT sent to any cloud service

### Database Schema
```sql
CREATE TABLE feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rating          INTEGER CHECK(rating >= 1 AND rating <= 5),
    suggestions     TEXT DEFAULT '',
    submitted_date  TEXT DEFAULT (date('now'))
);
```

### Columns
- `id` - Unique feedback entry ID
- `rating` - User rating from 1 (Poor) to 5 (Excellent)
- `suggestions` - User's text feedback/suggestions
- `submitted_date` - Date the feedback was submitted

## How to Access Feedback

### Method 1: SQLite Command Line (easiest)
```bash
# View all feedback
sqlite3 vinyl.db "SELECT * FROM feedback;"

# View with formatted output
sqlite3 vinyl.db ".mode column" "SELECT id, rating, suggestions, submitted_date FROM feedback;"

# Count feedback entries
sqlite3 vinyl.db "SELECT COUNT(*) FROM feedback;"

# Get average rating
sqlite3 vinyl.db "SELECT AVG(rating) FROM feedback;"
```

### Method 2: Python Script
```python
import sqlite3

conn = sqlite3.connect('vinyl.db')
cursor = conn.cursor()

# Get all feedback
cursor.execute("SELECT id, rating, suggestions, submitted_date FROM feedback")
for row in cursor.fetchall():
    print(row)

conn.close()
```

### Method 3: API Endpoint
```bash
# Retrieve all feedback via API
curl https://127.0.0.1:5000/api/feedback

# Response format:
[
  {
    "id": 1,
    "rating": 5,
    "suggestions": "Great app, very useful!",
    "submitted_date": "2026-04-11"
  },
  {
    "id": 2,
    "rating": 4,
    "suggestions": "Works well, could use dark mode",
    "submitted_date": "2026-04-11"
  }
]
```

## Exporting Feedback

### Export to CSV
```bash
# Using sqlite3-cli
sqlite3 vinyl.db "SELECT id, rating, suggestions, submitted_date FROM feedback;" | sed 's/|/,/g' > feedback.csv
```

### Export to JSON
```bash
# The /api/export/share endpoint includes feedback in its data export
curl -k https://127.0.0.1:5000/api/export/share > collection_data.json
```

### Export to Excel
1. Open `vinyl.db` with a SQLite browser (e.g., DB Browser for SQLite)
2. Select the `feedback` table
3. Export to CSV
4. Open the CSV in Excel

## Programmatic Access

### Submit Feedback via API
```bash
curl -k -X POST https://127.0.0.1:5000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "suggestions": "Excellent work!"
  }'
```

### Get Feedback via API
```bash
curl -k https://127.0.0.1:5000/api/feedback
```

## Database Backup

Since feedback is stored locally, regular backups are important:

### Windows
```bash
# Copy the database file
copy vinyl.db vinyl.db.backup

# Or schedule with Task Scheduler for automatic backups
```

### macOS/Linux
```bash
# Copy the database file
cp vinyl.db vinyl.db.backup

# Or use cron for automatic backups
# Add to crontab: 0 2 * * * cp /path/to/vinyl.db /path/to/vinyl.db.backup
```

## Feedback Data Privacy

- ✅ Feedback **NEVER** leaves your computer
- ✅ Feedback is **NOT** sent to any server
- ✅ You have **FULL** control of your feedback data
- ✅ Delete feedback anytime from the database
- ✅ Export/import your data as needed

## Deleting Feedback

### Delete a Specific Entry
```bash
# Delete feedback with ID 1
sqlite3 vinyl.db "DELETE FROM feedback WHERE id=1;"
```

### Delete All Feedback
```bash
# Clear the entire feedback table
sqlite3 vinyl.db "DELETE FROM feedback;"
```

### Delete and Rebuild Table
```bash
# Advanced: reset the table
sqlite3 vinyl.db "DROP TABLE feedback;" 
# Will be recreated on next app restart
```

## Analytics

### Get Feedback Statistics
```bash
# Average rating
sqlite3 vinyl.db "SELECT AVG(rating) as avg_rating, COUNT(*) as total_feedback FROM feedback;"

# Rating distribution
sqlite3 vinyl.db "SELECT rating, COUNT(*) as count FROM feedback GROUP BY rating ORDER BY rating DESC;"

# Feedback over time
sqlite3 vinyl.db "SELECT DATE(submitted_date) as date, COUNT(*) as count FROM feedback GROUP BY DATE(submitted_date);"
```

## Troubleshooting

### Can't access /api/feedback
- Ensure the app is running on HTTPS
- Check that you're using the correct port (default 5000)
- Verify the app is running: `ps aux | grep python`

### Database locked error
- Close the app and any other processes accessing vinyl.db
- On Windows, use Task Manager to end any lingering processes
- Try: `sqlite3 vinyl.db ".quit"` to release locks

### Can't open vinyl.db
- Install SQLite: [sqlite.org/download](https://sqlite.org/download.html)
- On Windows: Use "DB Browser for SQLite" GUI tool
- Or use command: `sqlite3 vinyl.db` (should work if Python's sqlite3 is installed)

## See Also

- [FEATURES.md](../FEATURES.md) - Overview of all features
- [README.txt](README.txt) - General setup instructions
- [test_vinyl_collection.py](test_vinyl_collection.py) - Test suite with examples
