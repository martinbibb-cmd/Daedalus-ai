import os
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import platform_queue_worker as worker


class FakeResponse:
    def __init__(self, status_code, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class PlatformQueueWorkerTests(unittest.TestCase):
    def bridge_environment(self):
        return mock.patch.dict(
            os.environ,
            {
                "CF_ACCESS_CLIENT_ID": "test-client-id",
                "CF_ACCESS_CLIENT_SECRET": "test-client-secret",
                "MANUAL_RIPPER_BRIDGE_KEY": "test-bridge-key",
            },
            clear=False,
        )

    def test_platform_headers_require_all_scoped_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CF_ACCESS_CLIENT_ID"):
                worker.platform_headers()

    def test_empty_queue_is_a_successful_noop(self):
        with self.bridge_environment(), mock.patch.object(
            worker.requests, "get", return_value=FakeResponse(204)
        ) as get:
            self.assertFalse(worker.process_one())

        self.assertIn("/manual-ripper/jobs/next", get.call_args.args[0])

    def test_invalid_queue_object_is_failed_closed(self):
        response = FakeResponse(
            200,
            content=b"not a pdf",
            headers={
                "x-daedalus-manual-id": "manual%3Ainvalid",
                "x-daedalus-source-filename": "invalid.pdf",
            },
        )
        with self.bridge_environment(), mock.patch.object(
            worker.requests, "get", return_value=response
        ), mock.patch.object(worker, "submit_failure") as fail:
            self.assertTrue(worker.process_one())

        fail.assert_called_once_with("manual:invalid", "Queued object is not a valid PDF.")


if __name__ == "__main__":
    unittest.main()
