# System Health Monitor

A Python-based system monitoring application that exposes HTTP endpoints for service health checks and system resource metrics. This project is being developed to demonstrate practical skills in Networking, Linux, Docker, CI/CD, and Cloud Computing.

## Current Features

- **Health endpoint:** Returns the application status and timestamp.
- **System metrics:** Reports CPU utilization, memory usage, disk usage, hostname, and application uptime.
- **HTTP error handling:** Returns HTTP 404 for unsupported endpoints.
- **Automated tests:** Tests health checks, metrics responses, and invalid endpoints.
- **Dependency management:** Uses a Python virtual environment and `requirements.txt`.

## Technology Stack

- Python 3.13
- Python `http.server`
- `psutil`
- Git and GitHub
- Python `unittest`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Returns the application health status |
| GET | `/metrics` | Returns system resource metrics |
| GET | `/invalid` | Example of an unsupported endpoint returning HTTP 404 |

## Prerequisites

- Python 3.13 or a compatible Python 3 version
- Git

## Run Locally on Windows

Clone the repository:

```powershell
git clone https://github.com/sangamesh-19/system-health-monitor.git
cd system-health-monitor
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the application:

```powershell
python app.py
```

Open another terminal and test the health endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Test the metrics endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/metrics
```

## Run Automated Tests

With the virtual environment activated, execute:

```powershell
python -m unittest -v test_app.py
```

The test suite checks successful health responses, system metrics, and HTTP 404 handling.

## Project Roadmap

The following capabilities are planned and will be added and verified during development:

- [ ] Linux administration and troubleshooting
- [ ] Docker containerization
- [ ] GitHub Actions CI/CD workflow
- [ ] Cloud deployment on AWS or Azure
- [ ] Deployment and networking documentation

## Repository

GitHub: https://github.com/sangamesh-19/system-health-monitor

## Learning Objective

The objective is to build a practical operations project that demonstrates service health checks, system monitoring, automated testing, version control, containerization, CI/CD, and cloud deployment.

**Project status:** In development.