# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY env.example .env

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/temp

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (if needed for health check)
EXPOSE 8000

# Create user for security with specific UID/GID
RUN groupadd --gid 1000 bot && \
    useradd --create-home --shell /bin/bash --uid 1000 --gid 1000 bot && \
    chown -R bot:bot /app
USER bot

# Start command
CMD ["python", "src/main.py"]
