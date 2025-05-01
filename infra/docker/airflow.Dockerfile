# ----------------------------------------------------------------------
# KnightShift Airflow container
# Extends the Apache Airflow image with project code and dependencies.
# ----------------------------------------------------------------------

FROM apache/airflow:2.8.1-python3.10

WORKDIR /opt/airflow

# Copy and install Python requirements
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code (for DAG imports or shared utils)
COPY knightshift/ ./knightshift/
