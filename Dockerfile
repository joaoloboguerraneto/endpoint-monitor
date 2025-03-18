FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY endpoint_monitor.py .

# Make the script executable
RUN chmod +x endpoint_monitor.py

# Create a symbolic link in a directory that's in PATH
RUN ln -s /app/endpoint_monitor.py /usr/local/bin/endpoint-monitor

# Set the entrypoint
ENTRYPOINT ["endpoint-monitor"]

# Default command (shows help)
CMD ["--help"]