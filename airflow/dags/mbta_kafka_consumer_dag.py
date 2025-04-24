from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
from mbta_kafka_consumer import consume_messages


# Import the consume_messages function from your Kafka consumer script
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))


# Logging setup
logging.basicConfig(level=logging.INFO)

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Define DAG
with DAG(
    dag_id='mbta_kafka_consumer_dag',
    default_args=default_args,
    description='Consume MBTA data from Kafka and load into Snowflake',
    schedule_interval='*/5 * * * *',  # Or adjust based on your real-time needs
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=['mbta', 'kafka', 'snowflake', 'consumer']
) as dag:

    run_consumer = PythonOperator(
        task_id='run_kafka_consumer',
        python_callable=consume_messages
    )

    run_consumer
