# System Health Monitor

A Python-based system monitoring application with a live web dashboard for monitoring CPU utilization, memory usage, disk usage, application uptime, and service health.

The project demonstrates practical skills in Python, Linux, Docker, automated testing, GitHub Actions, container registries, and AWS cloud deployment.

## Dashboard Preview

The application provides a dark-themed operations dashboard featuring:

- Live CPU, memory, and disk utilization.
- CPU and memory performance history charts.
- Application health status and uptime.
- Server hostname and monitoring status.
- HTTP health-check and metrics endpoints.
- Automatic dashboard refresh every 5 seconds.

## Architecture

```text
Developer
   |
   v
Git and GitHub
   |
   v
GitHub Actions CI/CD
   |
   +--> Run Python unit tests
   |
   +--> Build Docker image
   |
   +--> Publish image to GHCR
             |
             v
     GitHub Container Registry
             |
             v
       AWS Lightsail
             |
             v
   Docker container running
   System Health Monitor
             |
             v
      Web dashboard
```

**Note:** The current workflow publishes the Docker image. The AWS deployment is performed manually by pulling the image and replacing the running container.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.13 | Application backend |
| `http.server` | HTTP server and API endpoints |
| `psutil` | System resource monitoring |
| HTML, CSS, JavaScript | Interactive dashboard |
| Git and GitHub | Version control and source hosting |
| Python `unittest` | Automated testing |
| Docker | Application containerization |
| GitHub Actions | CI/CD automation |
| GitHub Container Registry (GHCR) | Docker image storage |
| AWS Lightsail | Cloud deployment |
| Ubuntu | Cloud server operating system |

## Features

- **Health monitoring:** Provides an HTTP endpoint to check application availability.
- **Resource monitoring:** Reports CPU, memory, and disk utilization.
- **Live dashboard:** Displays resource metrics and performance history.
- **REST-style HTTP endpoints:** Provides JSON responses for health and metrics.
- **Error handling:** Returns HTTP 404 for unsupported endpoints.
- **Automated testing:** Tests health checks, metrics, and invalid endpoints.
- **Container health checks:** Docker periodically checks application health.
- **Non-root container:** Runs the application as a dedicated, non-root user.
- **Automated image publishing:** GitHub Actions publishes the Docker image to GHCR.
- **Cloud deployment:** Runs the container on AWS Lightsail.

## API Documentation

All endpoints use the HTTP `GET` method.

| Endpoint | Description |
|---|---|
| `/` | Serves the web dashboard |
| `/health` | Returns service health and a timestamp |
| `/metrics` | Returns CPU, memory, disk, hostname, uptime, and timestamp |
| Any unsupported path | Returns HTTP 404 |

### Health endpoint

Example request:

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "healthy",
  "service": "System Health Monitor",
  "timestamp": "2026-10-22T20:08:30.991039+00:00"
}
```

The timestamp will vary for each request.

### Metrics endpoint

Example request:

```bash
curl http://localhost:8000/metrics
```

The response includes:

- `hostname`
- `cpu_percent`
- `memory.total_mb`
- `memory.used_mb`
- `memory.percent`
- `disk.total_gb`
- `disk.used_gb`
- `disk.percent`
- `uptime_seconds`
- `timestamp`

Metrics describe the environment in which the application runs. When containerized, the reported values may reflect container or host resource information depending on the operating system and container configuration.

## Prerequisites

For local development:

- Python 3.13 or a compatible Python version.
- Git.
- A terminal such as PowerShell.

For container deployment:

- Docker Desktop or Docker Engine.
- A running Docker daemon.

## Run Locally on Windows

### 1. Clone the repository

```powershell
git clone https://github.com/sangamesh-19/system-health-monitor.git
cd system-health-monitor
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Start the application

Use port 8001 if port 8000 is already occupied:

```powershell
$env:PORT="8001"
python app.py
```

Open the dashboard:

```text
http://localhost:8001/
```

Test the health endpoint in another terminal:

```powershell
Invoke-RestMethod http://localhost:8001/health
```

Test the metrics endpoint:

```powershell
Invoke-RestMethod http://localhost:8001/metrics
```

Stop the application with `Ctrl + C`.

## Automated Tests

Run the unit tests from the project directory:

```powershell
python -m unittest -v test_app.py
```

The current test suite covers:

- Successful health endpoint responses.
- Successful metrics endpoint responses.
- HTTP 404 responses for unsupported endpoints.

## Docker

### Build the image

```bash
docker build -t system-health-monitor:latest .
```

### Run the container

```bash
docker run -d \
  --name system-health-monitor \
  --restart unless-stopped \
  -p 8000:8000 \
  system-health-monitor:latest
```

### Verify the container

```bash
docker ps
docker logs system-health-monitor
```

### Test the application

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Open the dashboard at:

```text
http://localhost:8000/
```

### Stop and remove the container

```bash
docker stop system-health-monitor
docker rm system-health-monitor
```

If a container with that name already exists, remove or rename it before running another container with the same name.

## CI/CD with GitHub Actions

The GitHub Actions workflow automates key validation and image-publishing steps when changes are pushed to `main` or a pull request targets `main`, according to the workflow configuration.

The pipeline includes:

1. Checking out the repository.
2. Setting up Python and installing dependencies.
3. Running automated unit tests.
4. Building the Docker image.
5. Starting a test container and validating its health.
6. Publishing the image to GitHub Container Registry when the configured publishing conditions are met.

View workflow runs:

https://github.com/sangamesh-19/system-health-monitor/actions

## Docker Image

The published image is available at:

```text
ghcr.io/sangamesh-19/system-health-monitor:latest
```

Pull the image:

```bash
docker pull ghcr.io/sangamesh-19/system-health-monitor:latest
```

Run it:

```bash
docker run -d \
  --name system-health-monitor \
  --restart unless-stopped \
  -p 8000:8000 \
  ghcr.io/sangamesh-19/system-health-monitor:latest
```

If the GHCR package is private, authenticate with an authorized GitHub account before pulling the image.

## AWS Lightsail Deployment

The application has been deployed to an Ubuntu instance on AWS Lightsail using Docker.

The deployment process is:

1. Create an Ubuntu Lightsail instance.
2. Install and enable Docker Engine.
3. Pull the published image from GHCR.
4. Run the application container with port 8000 published.
5. Verify the container health status.
6. Test the health endpoint.
7. Open the dashboard using the instance's public IPv4 address and port 8000.

Example health check on the server:

```bash
curl http://localhost:8000/health
```

Example container command:

```bash
sudo docker run -d \
  --name system-health-monitor \
  --restart unless-stopped \
  -p 8000:8000 \
  ghcr.io/sangamesh-19/system-health-monitor:latest
```

To access the dashboard, use:

```text
http://YOUR-PUBLIC-IP:8000/
```

Replace `YOUR-PUBLIC-IP` with the instance's current public IPv4 address. An inbound TCP rule for port 8000 is required for public access.

### Cloud security considerations

- The current demonstration uses HTTP rather than HTTPS.
- Do not send credentials, API keys, or sensitive data through this application.
- Restrict public access to monitoring endpoints where appropriate.
- For a production deployment, configure HTTPS, review firewall rules, and use appropriate authentication and access controls.

## Troubleshooting

### Port already in use

If port 8000 is occupied locally, run the Python application on another port:

```powershell
$env:PORT="8001"
python app.py
```

### Container is unhealthy

Inspect the container and its logs:

```bash
docker ps
docker logs system-health-monitor
docker inspect system-health-monitor
```

### Dashboard file not found

Verify that the Dockerfile copies the dashboard into the image:

```dockerfile
COPY static/ ./static/
```

Rebuild the image after modifying the Dockerfile or dashboard.

### Docker daemon is unavailable

On Windows, check that Docker Desktop is running and that its Linux engine is available.

On Ubuntu, check Docker Engine:

```bash
sudo systemctl status docker
```

## Repository and CI/CD

**GitHub repository:**
https://github.com/sangamesh-19/system-health-monitor

**GitHub Actions:**
https://github.com/sangamesh-19/system-health-monitor/actions

## Skills Demonstrated

- Python application development.
- HTTP APIs and JSON responses.
- System resource monitoring.
- Unit testing and error handling.
- Git and GitHub workflows.
- Docker image creation and health checks.
- CI/CD with GitHub Actions.
- Container image publishing with GHCR.
- Linux server administration.
- AWS Lightsail deployment and basic networking.

## Future Improvements

- Configure HTTPS and secure public access.
- Add alerting when resource utilization crosses configurable thresholds.
- Add persistent historical metrics storage.
- Improve monitoring and application logging.
- Add automated deployment to AWS after successful CI/CD validation.
- Introduce a reverse proxy and domain name.
- Add integration tests and deployment verification.

## Learning Objective

This project demonstrates how to build, test, package, publish, deploy, and monitor a Python application using tools commonly encountered in DevOps, cloud support, and systems administration roles.
