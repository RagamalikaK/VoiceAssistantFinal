from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
import snowflake.connector
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from mbta_kafka_consumer import consume_messages




# Snowflake connection config
SNOWFLAKE_CONFIG = {
    "user": "CATFISH",
    "password": "Welcome1234#",
    "account": "pdb57018.us-west-2",
    "warehouse": "MBTA_WH2",
    "database": "MBTA_DB2",
    "schema": "MBTA_SCHEMA2",
}

# Dummy extraction function
def extract_from_kafka():
    logging.info("✅ Extracting data from Kafka... (dummy placeholder)")

# Dummy transformation function
def transform_data():
    logging.info("✅ Transforming data... (dummy placeholder)")

# Actual load function: creates table and inserts data into Snowflake
def load_to_snowflake():
    logging.info("🚀 Launching Kafka consumer to process and load data into Snowflake...")
    consume_messages()  # pulls and merges into Snowflake

# DAG default args
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Define DAG
with DAG(
    dag_id='mbta_ingestion_dag',
    default_args=default_args,
    description='ETL pipeline: MBTA data from Kafka to Snowflake',
    schedule='*/5 * * * *',
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=['mbta', 'kafka', 'snowflake'],
) as dag:

    extract_task = PythonOperator(
        task_id='extract_from_kafka',
        python_callable=extract_from_kafka,
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
    )

    load_task = PythonOperator(
        task_id='load_to_snowflake',
        python_callable=load_to_snowflake,
    )

    extract_task >> transform_task >> load_task
