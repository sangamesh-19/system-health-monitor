
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from collections import deque
from threading import Thread, Lock, Event
import json
import os
import shutil
import socket
import time

import psutil

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
START_TIME = time.time()

SAMPLE_INTERVAL = 5
MAX_HISTORY = 60
MAX_ALERTS = 50
WARNING_THRESHOLD = 70
CRITICAL_THRESHOLD = 85

history = deque(maxlen=MAX_HISTORY)
alerts = deque(maxlen=MAX_ALERTS)
data_lock = Lock()
stop_event = Event()

previous_severities = {}
latest_cpu_percent = 0.0


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def add_alert(key, description, severity):
    """Record severity changes and track alert recovery."""
    with data_lock:
        previous = previous_severities.get(key, "Info")

        if previous == severity:
            return

        previous_severities[key] = severity

        if previous in ("Warning", "Critical"):
            if severity == "Info":
                recovery_description = (
                    f"{key.upper()} utilization returned to normal"
                )
            else:
                recovery_description = (
                    f"{key.upper()} alert changed from "
                    f"{previous} to {severity}"
                )

            alerts.appendleft({
                "timestamp": timestamp(),
                "description": recovery_description,
                "severity": "Info",
                "status": "Resolved"
            })

        if severity in ("Warning", "Critical"):
            alerts.appendleft({
                "timestamp": timestamp(),
                "description": description,
                "severity": severity,
                "status": "Active"
            })


def collect_metrics():
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    with data_lock:
        cpu_percent = latest_cpu_percent

    return {
        "hostname": socket.gethostname(),
        "cpu_percent": cpu_percent,
        "memory": {
            "total_mb": round(memory.total / (1024 ** 2), 2),
            "used_mb": round(memory.used / (1024 ** 2), 2),
            "percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "percent": round(disk.used / disk.total * 100, 1)
        },
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "timestamp": timestamp()
    }


def severity_for(value):
    if value >= CRITICAL_THRESHOLD:
        return "Critical"
    if value >= WARNING_THRESHOLD:
        return "Warning"
    return "Info"


def sample_metrics():
    global latest_cpu_percent

    # Prime CPU measurement before collecting the first sample.
    psutil.cpu_percent(interval=None)
    next_sample = time.monotonic() + SAMPLE_INTERVAL

    while not stop_event.is_set():
        delay = next_sample - time.monotonic()

        if delay > 0 and stop_event.wait(delay):
            break

        if stop_event.is_set():
            break

        try:
            # Measure CPU over the elapsed sampling interval.
            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = shutil.disk_usage("/")

            memory_percent = memory.percent
            disk_percent = round(disk.used / disk.total * 100, 1)

            with data_lock:
                latest_cpu_percent = cpu
                history.append({
                    "timestamp": timestamp(),
                    "cpu_percent": cpu,
                    "memory_percent": memory_percent
                })

            for name, value in (
                ("cpu", cpu),
                ("memory", memory_percent),
                ("disk", disk_percent)
            ):
                severity = severity_for(value)
                description = (
                    f"{name.upper()} utilization is {value:.1f}%"
                )
                add_alert(name, description, severity)

        except Exception as error:
            print(f"Metrics sampling error: {error}")

        # Keep the schedule aligned to five-second intervals.
        next_sample += SAMPLE_INTERVAL

        # If processing fell behind, skip missed intervals rather
        # than generating rapid catch-up samples.
        now = time.monotonic()
        if next_sample <= now:
            missed = int((now - next_sample) // SAMPLE_INTERVAL) + 1
            next_sample += missed * SAMPLE_INTERVAL


class HealthMonitorHandler(BaseHTTPRequestHandler):

    def send_json(self, status_code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path

        try:
            if path == "/":
                dashboard = STATIC_DIR / "index.html"

                if not dashboard.is_file():
                    self.send_json(500, {
                        "error": "Dashboard file not found"
                    })
                    return

                body = dashboard.read_bytes()
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            elif path == "/health":
                self.send_json(200, {
                    "status": "healthy",
                    "service": "System Health Monitor",
                    "timestamp": timestamp()
                })

            elif path == "/metrics":
                self.send_json(200, collect_metrics())

            elif path == "/history":
                with data_lock:
                    samples = list(history)

                self.send_json(200, {
                    "interval_seconds": SAMPLE_INTERVAL,
                    "samples": samples
                })

            elif path == "/alerts":
                with data_lock:
                    recent_alerts = list(alerts)

                self.send_json(200, {"alerts": recent_alerts})

            else:
                self.send_json(404, {"error": "Endpoint not found"})

        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            print(f"Request error: {error}")
            try:
                self.send_json(500, {
                    "error": "Internal server error"
                })
            except (BrokenPipeError, ConnectionResetError):
                pass

    def log_message(self, format_string, *args):
        print(f"{self.client_address[0]} - {format_string % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))

    sampler = Thread(target=sample_metrics, daemon=True)
    sampler.start()

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthMonitorHandler
    )
    server.daemon_threads = True

    print(f"System Health Monitor running on port {port}")
    print(f"Dashboard: http://127.0.0.1:{port}/")
    print(f"Metrics:   http://127.0.0.1:{port}/metrics")
    print(f"History:   http://127.0.0.1:{port}/history")
    print(f"Alerts:    http://127.0.0.1:{port}/alerts")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down System Health Monitor")
    finally:
        stop_event.set()
        server.server_close()
