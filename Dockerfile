FROM python:3.11-slim

WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY endpoint_monitor.py .

# Make the script executable
RUN chmod +x endpoint_monitor.py

# Create a symbolic link in PATH
RUN ln -sf /app/endpoint_monitor.py /usr/local/bin/endpoint-monitor

# Set the directory for persistent storage
ENV CONFIG_DIR=/app/data
RUN mkdir -p $CONFIG_DIR

# Entry point for python directly
CMD ["python", "/app/endpoint_monitor.py"]