import json
import unittest
from http.client import HTTPConnection
from threading import Thread

import app_improved as app


class HostPulseTests(unittest.TestCase):
    def setUp(self):
        app.history.clear()
        app.alerts.clear()
        app.active_alerts.clear()
        app.previous_severities.clear()
        app.latest_metrics = None
        app.latest_cpu_percent = None
        app.last_sample_monotonic = None
        app.last_sample_timestamp = None
        app.last_collection_error = None
        app.total_collection_failures = 0

    def seed_metrics(self):
        now = app.timestamp()
        snapshot = {
            "service": app.SERVICE_NAME,
            "hostname": "test-host",
            "cpu_percent": 12.5,
            "memory": {"total_mb": 1000, "used_mb": 400, "percent": 40.0},
            "disk": {"total_gb": 100, "used_gb": 30, "percent": 30.0},
            "uptime_seconds": 1234,
            "timestamp": now,
        }
        app.latest_metrics = snapshot
        app.latest_cpu_percent = 12.5
        app.last_sample_monotonic = app.time.monotonic()
        app.last_sample_timestamp = now
        return snapshot

    def request(self, path):
        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            status = response.status
            connection.close()
            return status, json.loads(body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_health_starting_before_first_sample(self):
        status, body = self.request("/health")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "starting")
        self.assertFalse(body["metrics_ready"])

    def test_health_healthy_after_fresh_sample(self):
        self.seed_metrics()
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "healthy")
        self.assertTrue(body["metrics_ready"])
        self.assertFalse(body["metrics_stale"])

    def test_health_degraded_when_sample_stale(self):
        self.seed_metrics()
        app.last_sample_monotonic = app.time.monotonic() - (app.STALE_AFTER_SECONDS + 5)
        status, body = self.request("/health")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "degraded")
        self.assertTrue(body["metrics_stale"])

    def test_metrics_starting_before_first_sample(self):
        status, body = self.request("/metrics")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "starting")

    def test_metrics_returns_fresh_snapshot(self):
        snapshot = self.seed_metrics()
        status, body = self.request("/metrics")
        self.assertEqual(status, 200)
        self.assertEqual(body["cpu_percent"], snapshot["cpu_percent"])
        self.assertEqual(body["timestamp"], snapshot["timestamp"])
        self.assertFalse(body["collection"]["stale"])

    def test_metrics_stale_snapshot_returns_503(self):
        self.seed_metrics()
        app.last_sample_monotonic = app.time.monotonic() - (app.STALE_AFTER_SECONDS + 5)
        status, body = self.request("/metrics")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "degraded")
        self.assertTrue(body["collection"]["stale"])

    def test_metrics_collection_error_returns_503(self):
        self.seed_metrics()
        app.last_collection_error = "test collection failure"
        status, body = self.request("/metrics")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "degraded")
        self.assertEqual(body["collection"]["last_error"], "test collection failure")

    def test_history_starting_before_first_sample(self):
        status, body = self.request("/history")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "starting")
        self.assertEqual(body["count"], 0)

    def test_history_returns_samples(self):
        self.seed_metrics()
        app.history.append({
            "timestamp": app.last_sample_timestamp,
            "cpu_percent": 12.5,
            "memory_percent": 40.0,
        })
        status, body = self.request("/history")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["history"][0]["cpu_percent"], 12.5)

    def test_alert_created_for_warning(self):
        app.add_alert("cpu", "CPU usage is 75%", "Warning")
        self.assertEqual(len(app.alerts), 1)
        self.assertEqual(app.alerts[0]["status"], "Active")

    def test_severity_escalation_updates_same_incident(self):
        app.add_alert("cpu", "CPU usage is 75%", "Warning")
        original_id = app.active_alerts["cpu"]["id"]
        app.add_alert("cpu", "CPU usage is 90%", "Critical")
        self.assertEqual(len(app.alerts), 1)
        self.assertEqual(app.active_alerts["cpu"]["id"], original_id)
        self.assertEqual(app.active_alerts["cpu"]["severity"], "Critical")

    def test_recovery_resolves_original_incident_without_duplicate(self):
        app.add_alert("cpu", "CPU usage is 90%", "Critical")
        incident = app.active_alerts["cpu"]
        app.add_alert("cpu", "CPU usage is 20%", "Normal")
        self.assertNotIn("cpu", app.active_alerts)
        self.assertEqual(incident["status"], "Resolved")
        self.assertIsNotNone(incident["resolved_at"])
        self.assertEqual(len(app.alerts), 1)

    def test_same_severity_does_not_duplicate_incident(self):
        app.add_alert("memory", "Memory usage is 75%", "Warning")
        first_id = app.active_alerts["memory"]["id"]
        app.add_alert("memory", "Memory usage is 78%", "Warning")
        self.assertEqual(len(app.alerts), 1)
        self.assertEqual(app.active_alerts["memory"]["id"], first_id)

    def test_new_incident_after_recovery(self):
        app.add_alert("disk", "Disk usage is 90%", "Critical")
        first_id = app.active_alerts["disk"]["id"]
        app.add_alert("disk", "Disk usage is 40%", "Normal")
        app.add_alert("disk", "Disk usage is 90%", "Critical")
        self.assertEqual(len(app.alerts), 2)
        self.assertNotEqual(app.active_alerts["disk"]["id"], first_id)
        self.assertEqual(app.alerts[0]["status"], "Active")
        self.assertEqual(app.alerts[1]["status"], "Resolved")

    def test_unknown_endpoint_returns_404(self):
        status, body = self.request("/does-not-exist")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "Not found")

    def test_resource_severity_thresholds(self):
        self.assertEqual(app.resource_severity(69.9), "Normal")
        self.assertEqual(app.resource_severity(70), "Warning")
        self.assertEqual(app.resource_severity(84.9), "Warning")
        self.assertEqual(app.resource_severity(85), "Critical")


if __name__ == "__main__":
    unittest.main(verbosity=2)
