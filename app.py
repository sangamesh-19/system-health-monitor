
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from datetime import datetime, timezone


class HealthMonitorHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health":
            response = {
                "status": "healthy",
                "service": "System Health Monitor",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        else:
            response = {"error": "Endpoint not found"}

            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))


def main():
    server = HTTPServer(("127.0.0.1", 8000), HealthMonitorHandler)

    print("System Health Monitor is running!")
    print("Health endpoint: http://127.0.0.1:8000/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
