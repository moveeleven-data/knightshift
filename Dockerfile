# Use official slim Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependencies file and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code into the container
COPY src/ ./src/
COPY run.sh .

# Give the run.sh script execution permissions
RUN chmod +x run.sh

# Run the pipeline
ENTRYPOINT ["./run.sh"]