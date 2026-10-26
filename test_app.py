
import unittest
import json
from unittest.mock import patch

from app import (
    HealthMonitorHandler,
    add_alert,
    alerts,
    history,
    previous_severities,
    severity_for,
)


class TestHealthMonitor(unittest.TestCase):

    def setUp(self):
        self.handler = HealthMonitorHandler

    def test_health_endpoint(self):
        # Verify that the health endpoint is available.
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.request import urlopen

        server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/health"
            ) as response:
                data = json.loads(response.read())

            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "System Health Monitor")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_invalid_endpoint(self):
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.error import HTTPError
        from urllib.request import urlopen

        server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(
                    f"http://127.0.0.1:{server.server_port}/invalid"
                )

            self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_metrics_endpoint(self):
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.request import urlopen

        server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/metrics"
            ) as response:
                data = json.loads(response.read())

            self.assertIn("cpu_percent", data)
            self.assertIn("memory", data)
            self.assertIn("disk", data)
            self.assertIn("hostname", data)
            self.assertIn("uptime_seconds", data)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_severity_thresholds(self):
        self.assertEqual(severity_for(20), "Info")
        self.assertEqual(severity_for(70), "Warning")
        self.assertEqual(severity_for(84.9), "Warning")
        self.assertEqual(severity_for(85), "Critical")
        self.assertEqual(severity_for(100), "Critical")

    def test_warning_to_critical_transition(self):
        with patch("app.timestamp", return_value="test-time"):
            alerts.clear()
            previous_severities.clear()

            add_alert("cpu", "CPU is 75.0%", "Warning")
            add_alert("cpu", "CPU is 90.0%", "Critical")

            cpu_alerts = [
                alert for alert in alerts
                if alert["description"].startswith("CPU")
            ]

            self.assertEqual(len(cpu_alerts), 3)
            self.assertEqual(cpu_alerts[0]["severity"], "Critical")
            self.assertEqual(cpu_alerts[0]["status"], "Active")
            self.assertEqual(cpu_alerts[1]["status"], "Resolved")
            self.assertEqual(cpu_alerts[2]["severity"], "Warning")
            self.assertEqual(cpu_alerts[2]["status"], "Active")

    def test_resolve_alert_when_resource_returns_to_normal(self):
        with patch("app.timestamp", return_value="test-time"):
            alerts.clear()
            previous_severities.clear()

            add_alert("memory", "MEMORY utilization is 90%", "Critical")
            add_alert("memory", "MEMORY utilization is 40%", "Info")

            self.assertEqual(len(alerts), 2)
            self.assertEqual(alerts[0]["status"], "Resolved")
            self.assertEqual(alerts[1]["status"], "Active")

    def test_no_duplicate_alert_for_same_severity(self):
        with patch("app.timestamp", return_value="test-time"):
            alerts.clear()
            previous_severities.clear()

            add_alert("disk", "DISK utilization is 75%", "Warning")
            add_alert("disk", "DISK utilization is 78%", "Warning")

            self.assertEqual(len(alerts), 1)

    def test_history_endpoint_response_shape(self):
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.request import urlopen

        server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/history"
            ) as response:
                data = json.loads(response.read())

            self.assertEqual(data["interval_seconds"], 5)
            self.assertIn("samples", data)
            self.assertIsInstance(data["samples"], list)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
