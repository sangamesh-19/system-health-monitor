from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from collections import deque
from threading import Thread, Lock, Event
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
import shutil
import socket
import time
import psutil

SERVICE_NAME = "HostPulse System Health Monitor"
SAMPLE_INTERVAL = 5
MAX_HISTORY = 60
MAX_ALERTS = 50
WARNING_THRESHOLD = 70
CRITICAL_THRESHOLD = 85
STALE_AFTER_SECONDS = SAMPLE_INTERVAL * 3

history = deque(maxlen=MAX_HISTORY)
alerts = deque(maxlen=MAX_ALERTS)
active_alerts = {}
previous_severities = {}
data_lock = Lock()
stop_event = Event()

latest_metrics = None
latest_cpu_percent = None
last_sample_monotonic = None
last_sample_timestamp = None
last_collection_error = None
total_collection_failures = 0


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def add_alert(key, description, severity):
    """Keep one incident per key; update its status as the condition changes."""
    previous = previous_severities.get(key)
    previous_severities[key] = severity

    if severity in ("Warning", "Critical"):
        if key in active_alerts:
            incident = active_alerts[key]
            incident["severity"] = severity
            incident["description"] = description
            incident["updated_at"] = timestamp()
            incident["status"] = "Active"
            return

        incident = {
            "id": f"{key}-{time.time_ns()}",
            "key": key,
            "description": description,
            "severity": severity,
            "status": "Active",
            "created_at": timestamp(),
            "updated_at": timestamp(),
            "resolved_at": None,
        }
        active_alerts[key] = incident
        alerts.appendleft(incident)
        return

    if previous in ("Warning", "Critical") and key in active_alerts:
        incident = active_alerts.pop(key)
        incident["status"] = "Resolved"
        incident["resolved_at"] = timestamp()
        incident["updated_at"] = incident["resolved_at"]
        incident["description"] = f"{description} (recovered)"
        # The incident is already in alerts; update it in place instead of
        # appending the same object a second time to the historical list.


def resource_severity(value):
    if value >= CRITICAL_THRESHOLD:
        return "Critical"
    if value >= WARNING_THRESHOLD:
        return "Warning"
    return "Normal"


def collect_snapshot():
    cpu = latest_cpu_percent
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(Path.cwd())
    boot_time = psutil.boot_time()
    uptime_seconds = max(0, int(time.time() - boot_time))

    return {
        "service": SERVICE_NAME,
        "hostname": socket.gethostname(),
        "cpu_percent": cpu,
        "memory": {
            "total_mb": round(memory.total / (1024 * 1024), 2),
            "used_mb": round(memory.used / (1024 * 1024), 2),
            "percent": round(memory.percent, 2),
        },
        "disk": {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round((disk.total - disk.free) / (1024 ** 3), 2),
            "percent": round((disk.total - disk.free) / disk.total * 100, 2) if disk.total else 0,
        },
        "uptime_seconds": uptime_seconds,
        "timestamp": last_sample_timestamp,
        "collection": {
            "ready": latest_metrics is not None,
            "stale": is_metrics_stale(),
            "age_seconds": sample_age_seconds(),
            "last_error": last_collection_error,
            "failures": total_collection_failures,
        },
    }


def sample_age_seconds():
    if last_sample_monotonic is None:
        return None
    return round(max(0, time.monotonic() - last_sample_monotonic), 2)


def is_metrics_stale():
    age = sample_age_seconds()
    return age is None or age > STALE_AFTER_SECONDS


def sample_metrics():
    global latest_cpu_percent, latest_metrics
    global last_sample_monotonic, last_sample_timestamp
    global last_collection_error, total_collection_failures

    # Prime CPU measurement so the first displayed value is a real interval measurement.
    psutil.cpu_percent(interval=None)
    while not stop_event.wait(SAMPLE_INTERVAL):
        try:
            cpu = round(psutil.cpu_percent(interval=None), 2)
            memory = psutil.virtual_memory()
            disk = shutil.disk_usage(Path.cwd())
            now = timestamp()
            boot_time = psutil.boot_time()
            uptime = max(0, int(time.time() - boot_time))

            snapshot = {
                "service": SERVICE_NAME,
                "hostname": socket.gethostname(),
                "cpu_percent": cpu,
                "memory": {
                    "total_mb": round(memory.total / (1024 * 1024), 2),
                    "used_mb": round(memory.used / (1024 * 1024), 2),
                    "percent": round(memory.percent, 2),
                },
                "disk": {
                    "total_gb": round(disk.total / (1024 ** 3), 2),
                    "used_gb": round((disk.total - disk.free) / (1024 ** 3), 2),
                    "percent": round((disk.total - disk.free) / disk.total * 100, 2) if disk.total else 0,
                },
                "uptime_seconds": uptime,
                "timestamp": now,
            }

            with data_lock:
                latest_cpu_percent = cpu
                latest_metrics = snapshot
                last_sample_monotonic = time.monotonic()
                last_sample_timestamp = now
                last_collection_error = None
                history.append({
                    "timestamp": now,
                    "cpu_percent": cpu,
                    "memory_percent": snapshot["memory"]["percent"],
                })
                add_alert("cpu", f"CPU usage is {cpu}%", resource_severity(cpu))
                add_alert("memory", f"Memory usage is {snapshot['memory']['percent']}%",
                          resource_severity(snapshot["memory"]["percent"]))
                add_alert("disk", f"Disk usage is {snapshot['disk']['percent']}%",
                          resource_severity(snapshot["disk"]["percent"]))
        except Exception as exc:
            with data_lock:
                last_collection_error = str(exc)
                total_collection_failures += 1


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/":
            index_file = Path(__file__).parent / "static" / "index.html"
            if not index_file.exists():
                self.send_json({"error": "Dashboard file not found"}, 404)
                return
            html = index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(html)
            return

        if path == "/health":
            with data_lock:
                ready = latest_metrics is not None
                stale = is_metrics_stale()
                error = last_collection_error
                age = sample_age_seconds()

            if not ready:
                self.send_json({
                    "status": "starting" if error is None else "degraded",
                    "service": SERVICE_NAME,
                    "metrics_ready": False,
                    "message": "Waiting for the first successful metrics sample." if error is None else "Metrics collection has failed.",
                    "last_error": error,
                    "timestamp": timestamp(),
                }, 503)
            elif stale or error:
                self.send_json({
                    "status": "degraded",
                    "service": SERVICE_NAME,
                    "metrics_ready": True,
                    "metrics_stale": stale,
                    "sample_age_seconds": age,
                    "last_error": error,
                    "timestamp": timestamp(),
                }, 503)
            else:
                self.send_json({
                    "status": "healthy",
                    "service": SERVICE_NAME,
                    "metrics_ready": True,
                    "metrics_stale": False,
                    "sample_age_seconds": age,
                    "timestamp": timestamp(),
                })
            return

        if path == "/metrics":
            with data_lock:
                if latest_metrics is None:
                    self.send_json({
                        "status": "starting",
                        "message": "No successful metrics sample has been collected yet.",
                        "last_error": last_collection_error,
                    }, 503)
                    return
                if is_metrics_stale() or last_collection_error:
                    data = dict(latest_metrics)
                    data["collection"] = {
                        "ready": True,
                        "stale": is_metrics_stale(),
                        "age_seconds": sample_age_seconds(),
                        "last_error": last_collection_error,
                        "failures": total_collection_failures,
                    }
                    data["status"] = "degraded"
                    self.send_json(data, 503)
                    return
                data = dict(latest_metrics)
            data["collection"] = {
                "ready": True,
                "stale": False,
                "age_seconds": sample_age_seconds(),
                "last_error": None,
                "failures": total_collection_failures,
            }
            self.send_json(data)
            return

        if path == "/history":
            with data_lock:
                items = list(history)
                state = {
                    "interval_seconds": SAMPLE_INTERVAL,
                    "count": len(items),
                    "collection_stale": is_metrics_stale(),
                    "last_sample_timestamp": last_sample_timestamp,
                }
            state["history"] = items
            if not items:
                state["status"] = "starting"
                self.send_json(state, 503)
            else:
                self.send_json(state)
            return

        if path == "/alerts":
            with data_lock:
                result = list(alerts)
            self.send_json({"alerts": result, "count": len(result)})
            return

        self.send_json({"error": "Not found", "path": path}, 404)

    def log_message(self, format_string, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    sampler = Thread(target=sample_metrics, daemon=True)
    sampler.start()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"{SERVICE_NAME} is running on port {port}")
    print(f"Health endpoint: http://127.0.0.1:{port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()
