
import unittest
import json
import threading
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

    def test_health_endpoint(self):
        import urllib.request

        url = f"http://127.0.0.1:{self.port}/health"

        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)

            data = json.loads(response.read().decode("utf-8"))

            self.assertEqual(data["status"], "healthy")
            self.assertEqual(
                data["service"],
                "System Health Monitor"
            )
            self.assertIn("timestamp", data)

    def test_invalid_endpoint(self):
        import urllib.error
        import urllib.request

        url = f"http://127.0.0.1:{self.port}/invalid"

        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url)

        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
