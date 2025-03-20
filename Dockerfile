FROM python:3.11-slim

WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY endpoint_monitor.py .

# Make the script executable
RUN chmod +x endpoint_monitor.py

# Create a directory for persistent data storage
RUN mkdir -p /app/data

# Set environment variable to use the data directory
ENV CONFIG_DIR=/app/data

# Set the entrypoint
ENTRYPOINT ["python", "/app/endpoint_monitor.py"]

# Default command (shows help)
CMD ["--help"]