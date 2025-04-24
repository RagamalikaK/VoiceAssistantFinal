import json
import logging
from kafka import KafkaConsumer
import snowflake.connector
import pandas as pd
from datetime import datetime
import numpy as np
import time

# Kafka Configuration
KAFKA_BROKER = "kafka:9092"
TOPICS = ["mbta_alerts", "mbta_routes", "mbta_stops", "mbta_vehicles", "mbta_predictions", "mbta_schedules", "mbta_lines", "mbta_facilities"]

# Snowflake Configuration
SNOWFLAKE_CONFIG = {
    "user": "CATFISH",
    "password": "Welcome1234#",
    "account": "pdb57018.us-west-2",
    "warehouse": "MBTA_WH2",
    "database": "MBTA_DB2",
    "schema": "MBTA_SCHEMA2",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TABLE_MAPPING = {
    "MBTA_ALERTS": "MBTA_ALERTS",
    "MBTA_ROUTES": "MBTA_ROUTES",
    "MBTA_STOPS": "MBTA_STOPS",
    "MBTA_VEHICLES": "MBTA_VEHICLES",
    "MBTA_PREDICTIONS": "MBTA_PREDICTIONS",
    "MBTA_SCHEDULES": "MBTA_SCHEDULES",
    "MBTA_LINES": "MBTA_LINES",
    "MBTA_FACILITIES": "MBTA_FACILITIES"
}

KEY_MAPPING = {
    "MBTA_ALERTS": ["ALERT_ID"],
    "MBTA_ROUTES": ["ROUTE_ID"],
    "MBTA_STOPS": ["STOP_ID"],
    "MBTA_VEHICLES": ["VEHICLE_ID"],
    "MBTA_PREDICTIONS": ["PREDICTION_ID"],
    "MBTA_SCHEDULES": ["SCHEDULE_ID"],
    "MBTA_LINES": ["LINE_ID"],
    "MBTA_FACILITIES": ["FACILITY_ID"]
}


def connect_to_snowflake():
    try:
        conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
        logging.info("✅ Connected to Snowflake successfully.")
        return conn
    except Exception as e:
        logging.error(f"❌ Error connecting to Snowflake: {e}")
        exit(1)


def clean_data(df, table_name):
    df = df.where(pd.notnull(df), None)
    df = df.apply(lambda col: col.map(lambda x: None if isinstance(x, str) and x.strip().lower() in ('', 'none', 'nan', 'null') else x))
    logging.info(f"🔍 Sample data for {table_name}:")
    logging.info("\n%s", df.head())
    return df


def get_existing_records(conn, table, keys, ids):
    try:
        cursor = conn.cursor()
        key_col = keys[0]
        format_ids = ",".join(f"'{i}'" for i in ids)
        sql = f"SELECT * FROM {table} WHERE {key_col} IN ({format_ids})"
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        cursor.close()
        return df
    except Exception as e:
        logging.error(f"❌ Error fetching existing records from Snowflake: {e}")
        return pd.DataFrame()


def merge_into_snowflake(conn, table, df, keys):
    if df.empty:
        logging.info(f"⚠️ No new data for {table}, skipping merge.")
        return

    start_time = time.time()
    existing_df = get_existing_records(conn, table, keys, df[keys[0]].unique().tolist())

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
    for col in existing_df.columns:
        if pd.api.types.is_datetime64_any_dtype(existing_df[col]):
            existing_df[col] = existing_df[col].astype(str)

    df_combined = df.merge(existing_df, how="left", on=keys, suffixes=('', '_existing'), indicator=True)

    def row_changed(row):
        for col in df.columns:
            if col in keys or col == "CREATED_AT" or f"{col}_existing" not in row:
                continue
            if str(row[col]) != str(row[f"{col}_existing"]):
                return True
        return row["_merge"] == "left_only"

    df_filtered = df_combined[df_combined.apply(row_changed, axis=1)].copy()
    df_filtered = df_filtered[df.columns]

    logging.info(f"🔁 {len(df_filtered)} new/updated records out of {df.shape[0]} incoming records (some may be duplicates) for {table}")

    if df_filtered.empty:
        logging.info(f"✅ All {len(df)} records already up-to-date in {table}, no merge needed.")
        return

    cursor = conn.cursor()
    columns = df_filtered.columns.tolist()
    values = df_filtered.values.tolist()

    key_clause = " AND ".join([f"target.{k} = source.{k}" for k in keys])
    set_clause = ", ".join([f"{col} = source.{col}" for col in columns if col not in keys])
    column_list = ", ".join(columns)
    placeholder_list = ", ".join([f"%({col})s" for col in columns])

    for row in values:
        row_dict = dict(zip(columns, row))
        for k, v in row_dict.items():
            if isinstance(v, datetime):
                row_dict[k] = v.isoformat()
            elif isinstance(v, float) and (np.isnan(v) or pd.isnull(v)):
                row_dict[k] = None

        merge_sql = f"""
            MERGE INTO {table} AS target
            USING (SELECT {placeholder_list}) AS source ({column_list})
            ON {key_clause}
            WHEN MATCHED THEN UPDATE SET {set_clause}
            WHEN NOT MATCHED THEN INSERT ({column_list}) VALUES ({placeholder_list})
        """
        cursor.execute(merge_sql, row_dict)

    conn.commit()
    cursor.close()
    end_time = time.time()
    logging.info(f"✅ Merged {len(values)} new/changed records into Snowflake table: {table} in {end_time - start_time:.2f} seconds")


def handle_table_insert(conn, topic, data):
    if not data:
        logging.warning(f"⚠️ No data received for topic: {topic}")
        return

    try:
        topic_upper = topic.upper()
        table = TABLE_MAPPING.get(topic_upper)
        keys = KEY_MAPPING.get(topic_upper)

        if topic_upper == "MBTA_ALERTS":
            df = pd.DataFrame([{
                "ALERT_ID": d.get("id"),
                "HEADER": d["attributes"].get("header"),
                "DESCRIPTION": d["attributes"].get("description", ""),
                "EFFECT": d["attributes"].get("effect"),
                "SEVERITY": d["attributes"].get("severity"),
                "CREATED_AT": d["attributes"].get("created_at")
            } for d in data if d.get("id")])

        elif topic_upper == "MBTA_ROUTES":
            df = pd.DataFrame([{
                "ROUTE_ID": d.get("id"),
                "ROUTE_NAME": d["attributes"].get("long_name"),
                "ROUTE_TYPE": d["attributes"].get("type"),
                "ROUTE_COLOR": d["attributes"].get("color"),
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])

        elif topic_upper == "MBTA_STOPS":
            df = pd.DataFrame([{
                "STOP_ID": d.get("id"),
                "STOP_NAME": d["attributes"].get("name"),
                "LATITUDE": d["attributes"].get("latitude"),
                "LONGITUDE": d["attributes"].get("longitude"),
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])

        elif topic_upper == "MBTA_VEHICLES":
            df = pd.DataFrame([{
                "VEHICLE_ID": d.get("id"),
                "ROUTE_ID": d["relationships"].get("route", {}).get("data", {}).get("id"),
                "LATITUDE": d["attributes"].get("latitude"),
                "LONGITUDE": d["attributes"].get("longitude"),
                "BEARING": d["attributes"].get("bearing"),
                "SPEED": d["attributes"].get("speed"),
                "STATUS": d["attributes"].get("current_status"),
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])

        elif topic_upper == "MBTA_PREDICTIONS":
            df = pd.DataFrame([{
                "PREDICTION_ID": d.get("id"),
                "ROUTE_ID": d["relationships"].get("route", {}).get("data", {}).get("id"),
                "STOP_ID": d["relationships"].get("stop", {}).get("data", {}).get("id"),
                "VEHICLE_ID": d["relationships"].get("vehicle", {}).get("data", {}).get("id"),
                "DIRECTION_ID": d["attributes"].get("direction_id"),
                "ARRIVAL_TIME": d["attributes"].get("arrival_time"),
                "DEPARTURE_TIME": d["attributes"].get("departure_time"),
                "STATUS": d["attributes"].get("status"),
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])

        elif topic_upper == "MBTA_SCHEDULES":
            df = pd.DataFrame([{
                "SCHEDULE_ID": d.get("id"),
                "ARRIVAL_TIME": d["attributes"].get("arrival_time"),
                "DEPARTURE_TIME": d["attributes"].get("departure_time"),
                "STOP_SEQUENCE": d["attributes"].get("stop_sequence"),
                "PICKUP_TYPE": d["attributes"].get("pickup_type"),
                "DROP_OFF_TYPE": d["attributes"].get("drop_off_type"),
                "STOP_ID": d["relationships"].get("stop", {}).get("data", {}).get("id"),
                "TRIP_ID": d["relationships"].get("trip", {}).get("data", {}).get("id"),
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])


        elif topic_upper == "MBTA_LINES":
            df = pd.DataFrame([{
                "LINE_ID": d.get("id"),
                "LINE_NAME": d["attributes"].get("long_name"),
                "SORT_ORDER": d["attributes"].get("sort_order"),
                "DIRECTION_0": d["attributes"].get("direction_destinations", [None, None])[0],
                "DIRECTION_1": d["attributes"].get("direction_destinations", [None, None])[1],
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])


        elif topic_upper == "MBTA_FACILITIES":
            df = pd.DataFrame([{
                "FACILITY_ID": d.get("id"),
                "TYPE": d["attributes"].get("type"),
                "LONG_NAME": d["attributes"].get("long_name"),
                "SHORT_NAME": d["attributes"].get("short_name"),
                "LATITUDE": d["attributes"].get("latitude"),
                "LONGITUDE": d["attributes"].get("longitude"),
                "STOP_ID": d["relationships"].get("stop", {}).get("data", {}).get("id"),
                "CREATED_AT": datetime.utcnow()
            } for d in data if d.get("id")])

        else:
            logging.warning(f"❌ No handler for topic: {topic_upper}")
            return

        df = clean_data(df, topic_upper)
        merge_into_snowflake(conn, table, df, keys)

    except Exception as e:
        logging.error(f"❌ Error processing topic {topic}: {e}")


def consume_messages():
    conn = connect_to_snowflake()
    if not conn:
        return

    logging.info("🚀 Starting MBTA Kafka Consumer...")
    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=30000,
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )

    try:
        for message in consumer:
            topic = message.topic
            data = message.value
            logging.info(f"📥 Received {len(data)} records from topic: {topic}")
            handle_table_insert(conn, topic, data)
    except KeyboardInterrupt:
        logging.info("🛑 Stopping MBTA Kafka Consumer...")
    finally:
        consumer.close()
        conn.close()
        logging.info("✅ Snowflake Connection Closed.")


if __name__ == "__main__":
    consume_messages()


