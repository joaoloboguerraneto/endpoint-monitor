# Endpoint Monitor
A CLI tool to monitor the availability of websites and services.

## Features
- Add, monitor, and track website/service availability
- Run one-time scans of configured endpoints
- Continuously monitor endpoints at specified intervals
- View monitoring history in a table format
- Docker support for containerized deployment
- CI/CD integration with GitHub Actions

## Installation

### Local Installation with Virtual Environment (Recommended)
1. Ensure you have Python 3.10+ installed
2. Clone this repository
3. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
4. Install the dependencies:
```bash
pip install -r requirements.txt
```
5. Make the script executable:
```bash
chmod +x endpoint_monitor.py
```
6. (Optional) Create a symbolic link to run the tool from anywhere:
```bash
sudo ln -s $(pwd)/endpoint_monitor.py /usr/local/bin/endpoint-monitor
```

### MacOS Installation Note
If you're using a recent version of macOS, you may encounter an "externally-managed-environment" error when installing packages. This is because Python on newer macOS versions restricts direct package installation. Always use a virtual environment as shown above.

### Docker Installation
1. Build the Docker image:
```bash
docker build -t endpoint-monitor .
```
2. Run the container:
```bash
docker run -it endpoint-monitor
```

## Usage

### Adding Endpoints
Add a new endpoint to monitor:
```bash
./endpoint_monitor.py add-endpoint name https://example.com
```
With custom timeout:
```bash
./endpoint_monitor.py add-endpoint name https://example.com --timeout 15
```

### Scanning Endpoints
Scan all configured endpoints:
```bash
./endpoint_monitor.py fetch
```
Scan and display results:
```bash
./endpoint_monitor.py fetch --output
```
Scan specific endpoints:
```bash
./endpoint_monitor.py fetch --endpoints google github --output
```

### Live Monitoring
Monitor endpoints at regular intervals:
```bash
./endpoint_monitor.py live
```
With custom interval (in seconds):
```bash
./endpoint_monitor.py live --interval 30
```
Monitor specific endpoints with visible output:
```bash
./endpoint_monitor.py live --endpoints google github --output
```

### Viewing History
Show all monitoring history:
```bash
./endpoint_monitor.py history
```
Show history for specific endpoints:
```bash
./endpoint_monitor.py history --endpoints google github
```

### Docker Usage
The tool can be run within Docker:
```bash
# Show help
docker run endpoint-monitor
# Add an endpoint
docker run -v endpoint-data:/app/data endpoint-monitor add-endpoint google https://google.com
# Fetch all endpoints
docker run -v endpoint-data:/app/data endpoint-monitor fetch --output
# Show history
docker run -v endpoint-data:/app/data endpoint-monitor history
```

## Configuration
The tool stores its configuration in `~/.endpoint-monitor/config.json` and monitoring data in `~/.endpoint-monitor/data-store.csv`.

Sample configuration:
```json
{
    "endpoints": {
        "google": {
            "url": "https://www.google.com",
            "timeout": 5
        },
        "github": {
            "url": "https://github.com",
            "timeout": 10
        }
    }
}
```

### Editing Endpoints
To edit an existing endpoint (e.g., changing name or URL), you need to:

1. Edit the configuration file directly:
```bash
nano ~/.endpoint-monitor/config.json
```
2. Or add a new endpoint and remove the old one from the config file.

## Development

### Running Tests
```bash
pytest
```
With coverage:
```bash
pytest --cov=./
```

### CI/CD Integration
This project includes a GitHub Actions workflow that:
1. Runs tests on every push and pull request
2. Builds and tests the Docker image on main branch
3. Checks configured endpoints and reports status

## License
