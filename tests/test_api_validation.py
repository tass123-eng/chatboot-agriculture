import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


class ApiValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_chat_interface_is_available(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("AgriAI", response.text)

    def test_ask_rejects_empty_question(self):
        response = self.client.post("/ask", json={"question": ""})

        self.assertEqual(response.status_code, 422)

    def test_manual_diagnostic_rejects_invalid_confidence(self):
        response = self.client.post(
            "/diagnostic/manual",
            json={
                "crop": "tomate",
                "predicted_class": "tomato_mildiou",
                "confidence": 1.1,
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_image_upload_accepts_png(self):
        response = self.client.post(
            "/images/upload",
            files={"file": ("leaf.png", b"fake-png-content", "image/png")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        stored_file = Path(__file__).parent.parent / payload["file_path"]
        self.assertTrue(stored_file.exists())
        self.assertTrue(payload["url"].startswith("/uploads/"))
        stored_file.unlink()

    def test_database_errors_are_returned_as_json(self):
        with patch(
            "app.get_conn",
            side_effect=__import__("psycopg").OperationalError("database offline"),
        ):
            response = self.client.get("/diseases")

        self.assertEqual(response.status_code, 503)
        self.assertIn("PostgreSQL", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
