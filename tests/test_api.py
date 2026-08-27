import tempfile
import unittest

from fastapi.testclient import TestClient

from vsem_fms.app.config import settings
from vsem_fms.app.main import app


class FileApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_storage_path = settings.STORAGE_PATH
        settings.STORAGE_PATH = self.temp_dir.name
        self.client = TestClient(app)
        self.headers = {"X-API-Key": settings.API_KEY}

    def tearDown(self) -> None:
        self.client.close()
        settings.STORAGE_PATH = self.original_storage_path
        self.temp_dir.cleanup()

    def test_upload_list_get_delete_round_trip(self) -> None:
        upload = self.client.post(
            "/api/v1/files",
            headers=self.headers,
            data={"folder": "customer-1", "subfolder": "project-1", "overwrite": "true"},
            files={"file": ("hello.txt", b"hello world", "text/plain")},
        )
        self.assertEqual(upload.status_code, 201)
        self.assertEqual(upload.json()["path"], "customer-1/project-1/hello.txt")

        listing = self.client.get(
            "/api/v1/files/customer-1/project-1",
            headers=self.headers,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json(), {"files": ["hello.txt"]})

        retrieved = self.client.get(
            "/api/v1/files/customer-1/project-1/hello.txt",
            headers=self.headers,
        )
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json(), {"filename": "hello.txt", "content": "hello world"})

        deleted = self.client.delete(
            "/api/v1/files/customer-1/project-1/hello.txt",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 204)

        missing = self.client.get(
            "/api/v1/files/customer-1/project-1/hello.txt",
            headers=self.headers,
        )
        self.assertEqual(missing.status_code, 404)

    def test_invalid_upload_path_segment_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/files",
            headers=self.headers,
            data={"folder": "../customer", "subfolder": "project-1", "overwrite": "true"},
            files={"file": ("hello.txt", b"hello", "text/plain")},
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_api_key_is_rejected(self) -> None:
        response = self.client.get(
            "/api/v1/files/customer-1/project-1",
            headers={"X-API-Key": "wrong"},
        )
        self.assertEqual(response.status_code, 403)
