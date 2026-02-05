FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir ./backend

# Copy application code
COPY backend/app ./backend/app

# Copy levels directory (needed for level definitions)
COPY levels ./levels

WORKDIR /app/backend

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
