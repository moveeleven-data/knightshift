# Use official slim Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install PostgreSQL client tools (for pg_isready, etc.)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY src/ ./src/
COPY run.sh .

# Make run.sh executable
RUN chmod +x run.sh

# Run the pipeline
ENTRYPOINT ["./run.sh"]
