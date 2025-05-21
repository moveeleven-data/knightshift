FROM apache/airflow:2.8.1-python3.10

WORKDIR /opt/airflow

COPY requirements.txt .

RUN pip install --no-cache-dir apache-airflow==2.8.1 \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt" && \
    pip install --no-cache-dir -r requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"

COPY knightshift/ ./knightshift/
