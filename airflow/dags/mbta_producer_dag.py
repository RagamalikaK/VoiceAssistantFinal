from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys, os

sys.path.append(os.path.dirname(__file__))
from mbta_data_pipeline import main as produce_data

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='mbta_producer_dag',
    default_args=default_args,
    description='Fetch MBTA API data and send to Kafka',
    schedule_interval='*/5 * * * *',
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=['mbta', 'producer', 'kafka'],
) as dag:

    produce_task = PythonOperator(
        task_id='produce_mbta_data',
        python_callable=produce_data
    )
