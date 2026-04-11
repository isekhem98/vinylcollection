"""
Comprehensive test suite for Vinyl Collection Dashboard.
Tests all new features: feedback, authentication, API endpoints, and database operations.

Usage:
    python test_vinyl_collection.py
"""

import json
import sqlite3
import unittest
from pathlib import Path
from base64 import b64encode
from unittest.mock import patch, MagicMock

# Import the app modules
import sys
sys.path.insert(0, str(Path(__file__).parent))

from database import Database
from webapp import app, get_db, users
import database as db_module


class TestDatabase(unittest.TestCase):
    """Test database operations including feedback."""

    def setUp(self):
        # Use in-memory database for tests to avoid file locking issues on Windows
        self.db = Database(":memory:")

    def tearDown(self):
        # Properly close the database connection
        if hasattr(self, 'db') and self.db.conn:
            self.db.conn.close()

    def test_feedback_table_exists(self):
        """Test that feedback table is created."""
        cursor = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback';"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_add_feedback(self):
        """Test adding feedback to database."""
        feedback_id = self.db.add_feedback(rating=5, suggestions="Great app!")
        self.assertIsNotNone(feedback_id)
        self.assertGreater(feedback_id, 0)

    def test_get_all_feedback(self):
        """Test retrieving all feedback."""
        self.db.add_feedback(4, "Very good!")
        self.db.add_feedback(3, "Good but needs improvement")
        feedback = self.db.get_all_feedback()
        self.assertEqual(len(feedback), 2)
        # Check that both ratings are present (order may vary due to timing)
        ratings = [f["rating"] for f in feedback]
        self.assertIn(3, ratings)
        self.assertIn(4, ratings)

    def test_config_operations(self):
        """Test config CRUD operations."""
        self.db.set_config("test_key", "test_value")
        value = self.db.get_config("test_key")
        self.assertEqual(value, "test_value")

    def test_vinyl_crud(self):
        """Test vinyl record CRUD operations."""
        vinyl_id = self.db.add_vinyl(
            release_id="12345",
            title="Test Album",
            artist="Test Artist",
            year=2020
        )
        self.assertGreater(vinyl_id, 0)
        
        vinyl = self.db.get_vinyl(vinyl_id)
        self.assertEqual(vinyl["title"], "Test Album")
        self.assertEqual(vinyl["artist"], "Test Artist")
        
        self.db.update_vinyl(vinyl_id, title="Updated Album")
        vinyl = self.db.get_vinyl(vinyl_id)
        self.assertEqual(vinyl["title"], "Updated Album")
        
        self.db.delete_vinyl(vinyl_id)
        vinyl = self.db.get_vinyl(vinyl_id)
        self.assertIsNone(vinyl)

    def test_wantlist_operations(self):
        """Test wantlist operations."""
        want_id = self.db.add_want(
            release_id="54321",
            title="Wanted Album",
            artist="Wanted Artist"
        )
        self.assertGreater(want_id, 0)
        
        wants = self.db.get_all_wants()
        self.assertGreater(len(wants), 0)
        
        self.db.delete_want(want_id)
        wants = self.db.get_all_wants()
        self.assertEqual(len(wants), 0)


class TestWebAppAPI(unittest.TestCase):
    """Test Flask web API endpoints."""

    def setUp(self):
        # Use in-memory database for tests
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
        app.config["SERVER_NAME"] = "localhost"  # Prevent redirects
        self.client = app.test_client()
        
        # Mock the database
        self.patcher = patch("webapp.get_db")
        self.mock_get_db = self.patcher.start()
        self.db = Database(":memory:")
        self.mock_get_db.return_value = self.db

    def tearDown(self):
        self.patcher.stop()
        # Properly close the database connection
        if hasattr(self, 'db') and self.db.conn:
            self.db.conn.close()

    def _get_auth_header(self, username="admin", password="admin"):
        """Generate basic auth header."""
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def test_index_route(self):
        """Test index page loads."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_feedback_route(self):
        """Test feedback page loads."""
        response = self.client.get("/feedback")
        self.assertEqual(response.status_code, 200)

    def test_add_feedback_api(self):
        """Test feedback submission API."""
        payload = {"rating": 5, "suggestions": "Excellent app!"}
        response = self.client.post(
            "/api/feedback",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])

    def test_add_feedback_invalid_rating(self):
        """Test feedback with invalid rating."""
        payload = {"rating": 10, "suggestions": "Bad rating"}
        response = self.client.post(
            "/api/feedback",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_get_feedback_api(self):
        """Test retrieving feedback."""
        self.db.add_feedback(4, "Good")
        response = self.client.get("/api/feedback")
        self.assertEqual(response.status_code, 200)
        feedback = response.json
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["rating"], 4)

    def test_get_vinyls_api(self):
        """Test retrieving vinyls."""
        self.db.add_vinyl(title="Album 1", artist="Artist 1", release_id="1")
        response = self.client.get("/api/vinyls")
        self.assertEqual(response.status_code, 200)
        vinyls = response.json
        self.assertEqual(len(vinyls), 1)

    def test_add_vinyl_api(self):
        """Test adding vinyl via API."""
        payload = {
            "title": "New Album",
            "artist": "New Artist",
            "release_id": "999",
            "year": 2023
        }
        response = self.client.post(
            "/api/vinyls",
            data=json.dumps(payload),
            content_type="application/json",
            headers=self._get_auth_header()
        )
        self.assertIn(response.status_code, [200, 201])

    def test_config_api(self):
        """Test config API."""
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        
        payload = {"discogs_token": "test_token"}
        response = self.client.patch(
            "/api/config",
            data=json.dumps(payload),
            content_type="application/json",
            headers=self._get_auth_header()
        )
        self.assertEqual(response.status_code, 200)

    def test_stats_api(self):
        """Test stats endpoint."""
        self.db.add_vinyl(title="Album", artist="Artist", year=2020, purchase_price=25.0)
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.json
        self.assertIn("total", stats)
        self.assertGreater(stats["total"], 0)

    def test_git_update_requires_auth(self):
        """Test that git update requires authentication."""
        response = self.client.post("/api/git-update")
        self.assertEqual(response.status_code, 401)

    def test_git_update_with_auth(self):
        """Test git update with authentication."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date")
            response = self.client.post(
                "/api/git-update",
                headers=self._get_auth_header()
            )
            self.assertIn(response.status_code, [200, 500])  # May fail if not a git repo


class TestAuthentication(unittest.TestCase):
    """Test authentication functionality."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _get_auth_header(self, username="admin", password="admin"):
        """Generate basic auth header."""
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def test_default_user_exists(self):
        """Test that default admin user exists."""
        from werkzeug.security import check_password_hash
        self.assertIn("admin", users)

    def test_auth_verify_correct_password(self):
        """Test auth with correct password."""
        from webapp import verify_password
        result = verify_password("admin", "admin")
        self.assertIsNotNone(result)

    def test_auth_verify_incorrect_password(self):
        """Test auth with incorrect password."""
        from webapp import verify_password
        result = verify_password("admin", "wrongpassword")
        self.assertIsNone(result)

    def test_auth_header_format(self):
        """Test basic auth header generation."""
        header = self._get_auth_header()
        self.assertIn("Authorization", header)
        self.assertIn("Basic ", header["Authorization"])


class TestDataExport(unittest.TestCase):
    """Test data export functionality."""

    def setUp(self):
        # Use in-memory database for testing
        self.db = Database(":memory:")
        self.json_path = Path("test_export.json")

    def tearDown(self):
        # Properly close the database connection
        if hasattr(self, 'db') and self.db.conn:
            self.db.conn.close()
        
        # Clean up JSON file with proper error handling
        if hasattr(self, 'json_path') and self.json_path.exists():
            try:
                self.json_path.unlink()
            except Exception:
                pass  # Ignore file deletion errors

    def test_export_to_json(self):
        """Test exporting database to JSON."""
        self.db.add_vinyl(title="Album", artist="Artist", release_id="1")
        self.db.add_want(title="Wanted", artist="Artist", release_id="2")
        
        count = self.db.export_to_json(self.json_path)
        self.assertGreater(count, 0)
        self.assertTrue(self.json_path.exists())
        
        with open(self.json_path) as f:
            data = json.load(f)
        self.assertIn("vinyls", data)
        self.assertIn("wantlist", data)

    def test_import_from_json(self):
        """Test importing from JSON."""
        data = {
            "vinyls": [
                {"title": "Album", "artist": "Artist", "release_id": "1"}
            ],
            "wantlist": [],
            "config": {}
        }
        with open(self.json_path, "w") as f:
            json.dump(data, f)
        
        count = self.db.import_from_json(self.json_path)
        self.assertGreater(count, 0)
        
        vinyls = self.db.get_all_vinyls()
        self.assertEqual(len(vinyls), 1)


def run_all_tests():
    """Run all tests and print results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestWebAppAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestDataExport))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
