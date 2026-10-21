
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import socket
import time
from datetime import datetime, timezone

import psutil


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

        if self.path == "/health":
            self.send_json(200, {
                "status": "healthy",
                "service": "System Health Monitor",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        elif self.path == "/metrics":
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(os.getcwd())

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
                    "percent": disk.percent
                },
                "uptime_seconds": round(time.time() - START_TIME, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        else:
            self.send_json(404, {
                "error": "Endpoint not found"
            })


def main():
    server = HTTPServer(
        ("127.0.0.1", 8000),
        HealthMonitorHandler
    )

    print("System Health Monitor is running!")
    print("Health endpoint: http://127.0.0.1:8000/health")
    print("Metrics endpoint: http://127.0.0.1:8000/metrics")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
