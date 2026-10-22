
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import socket
import time
import psutil

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
START_TIME = time.time()


class HealthMonitorHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            dashboard = STATIC_DIR / "index.html"

            if not dashboard.is_file():
                self.send_json(500, {"error": "Dashboard file not found"})
                return

            body = dashboard.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/health":
            self.send_json(200, {
                "status": "healthy",
                "service": "System Health Monitor",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        elif self.path == "/metrics":
            memory = psutil.virtual_memory()
            disk = shutil.disk_usage("/")

            self.send_json(200, {
                "hostname": socket.gethostname(),
                "cpu_percent": psutil.cpu_percent(interval=0.2),
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
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        else:
            self.send_json(404, {"error": "Endpoint not found"})

    def log_message(self, format_string, *args):
        print(f"{self.client_address[0]} - {format_string % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthMonitorHandler)
    print(f"System Health Monitor running on port {port}")
    server.serve_forever()
