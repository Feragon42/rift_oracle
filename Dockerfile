FROM apache/airflow:3.3.1-python3.11

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        chromium \
        chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/airflow

COPY requirements.txt /requirements.txt

USER airflow

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt

USER root

COPY . /opt/airflow
RUN chown -R airflow:root /opt/airflow

USER airflow

ENV PYTHONPATH=/opt/airflow \
    AIRFLOW__CORE__LOAD_EXAMPLES=False \
    AIRFLOW__CORE__EXECUTOR=LocalExecutor

EXPOSE 8080

CMD ["airflow", "standalone"]

