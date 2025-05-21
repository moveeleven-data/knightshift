# Use Python 3.10 slim as the base image
FROM python:3.10-slim

# Install system dependencies required by psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*  # Clean up after install to reduce image size

# Set the working directory
WORKDIR /app

# Copy the Flask app and requirements file into the container
COPY . /app

# Install the necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 (the default Flask port)
EXPOSE 5000

# Run the Flask app when the container starts
CMD ["python", "app.py"]
