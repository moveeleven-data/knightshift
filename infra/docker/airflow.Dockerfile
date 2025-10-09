# =============================================================================
#  KnightShift Airflow Image
#  Base: Apache Airflow 2.8.1 with Python 3.10
# =============================================================================
FROM apache/airflow:2.8.1-python3.10

# Set working directory
WORKDIR /opt/airflow

# -----------------------------------------------------------------------------
# Install dependencies
#   1. Pin Apache Airflow version with official constraints
#   2. Install project-specific requirements
# -----------------------------------------------------------------------------
COPY requirements.txt .

RUN pip install --no-cache-dir apache-airflow==2.8.1 \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt" \
    && pip install --no-cache-dir -r requirements.txt \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"

# -----------------------------------------------------------------------------
# Copy project source
# -----------------------------------------------------------------------------
COPY knightshift/ ./knightshift/
