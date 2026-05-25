# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to ensure Python output is logged immediately
# and bytecode isn't written to disk
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for psycopg2 and building packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production serving (even though we might use runserver for dev)
RUN pip install gunicorn

# Copy the backend code into the container
COPY arcx_backend /app/arcx_backend

# Change working directory to where manage.py lives
WORKDIR /app/arcx_backend

# Expose port 8000 for the Django server
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml for Celery workers)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
