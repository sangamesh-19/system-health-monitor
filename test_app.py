
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer

from app import HealthMonitorHandler


class TestHealthMonitor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(
            ("127.0.0.1", 0),
            HealthMonitorHandler
        )

        cls.port = cls.server.server_address[1]

        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get_json(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"

        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            return response.status, data

    def test_health_endpoint(self):
        status, data = self.get_json("/health")

        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "System Health Monitor")
        self.assertIn("timestamp", data)

    def test_metrics_endpoint(self):
        status, data = self.get_json("/metrics")

        self.assertEqual(status, 200)
        self.assertIn("hostname", data)
        self.assertIn("cpu_percent", data)
        self.assertIn("memory", data)
        self.assertIn("disk", data)
        self.assertIn("uptime_seconds", data)

        self.assertGreaterEqual(data["cpu_percent"], 0)
        self.assertGreaterEqual(data["memory"]["percent"], 0)
        self.assertGreaterEqual(data["disk"]["percent"], 0)

    def test_invalid_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/invalid"

        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url)

        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
