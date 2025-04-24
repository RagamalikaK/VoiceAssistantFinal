# import requests
# import json
# import time
# import logging
# from kafka import KafkaProducer

# # ✅ MBTA API Configuration
# MBTA_API_KEY = "6426e442cb644cae82e86def2e03ecb3"
# MBTA_API_URL = "https://api-v3.mbta.com"

# # ✅ Kafka Configuration
# KAFKA_BROKER = "kafka:9092"
# TOPICS = {
#     "alerts": "mbta_alerts",
#     "routes": "mbta_routes",
#     "stops": "mbta_stops",
#     "vehicles": "mbta_vehicles",
#     "predictions": "mbta_predictions",

# }

# # ✅ Setup logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# # ✅ Kafka Producer Setup
# def create_kafka_producer():
#     for _ in range(10):
#         try:
#             producer = KafkaProducer(
#                 bootstrap_servers=KAFKA_BROKER,
#                 linger_ms=500,
#                 batch_size=16384,
#                 max_request_size=5000000,
#                 acks="all",
#                 value_serializer=lambda v: json.dumps(v).encode("utf-8")
#             )
#             logging.info("✅ Kafka Producer connected successfully.")
#             return producer
#         except Exception as e:
#             logging.error(f"❌ Kafka Producer connection failed: {e}")
#             time.sleep(5)
#     exit(1)

# producer = create_kafka_producer()


# # ✅ Define API Endpoints
# ENDPOINTS = {
#     "alerts": f"/alerts?include=route&api_key={MBTA_API_KEY}",
#     "routes": f"/routes?api_key={MBTA_API_KEY}",
#     "stops": f"/stops?api_key={MBTA_API_KEY}",
#     "vehicles": f"/vehicles?api_key={MBTA_API_KEY}",
#     "predictions": f"/predictions?include=route,stop,vehicle&api_key={MBTA_API_KEY}"
# }



# # ✅ Helper to chunk large data lists
# def chunk_records(data, chunk_size=1000):
#     for i in range(0, len(data), chunk_size):
#         yield data[i:i + chunk_size]


# # ✅ Function to fetch & send data to Kafka
# def fetch_and_produce(topic, endpoint):
#     url = f"{MBTA_API_URL}{endpoint}"
#     try:
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()
#         data = response.json()

#         if not data.get("data"):
#             logging.warning(f"⚠️ No data returned from {endpoint}")
#             return

#         payload = data["data"]
#         payload_size_kb = len(json.dumps(payload).encode("utf-8")) / 1024
#         logging.info(f"📦 Payload size for {topic}: {payload_size_kb:.2f} KB")

#         if topic == "mbta_stops" and payload_size_kb > 4500:
#             logging.warning("⚠️ Splitting large payload into chunks...")
#             for chunk in chunk_records(payload, chunk_size=1000):
#                 producer.send(topic, chunk)
#                 producer.flush()
#         else:
#             producer.send(topic, payload)
#             producer.flush()

#         logging.info(f"✅ Data sent to Kafka topic: {topic} ({len(payload)} records)")

#     except requests.exceptions.RequestException as e:
#         logging.error(f"❌ Error fetching {endpoint}: {e}")
#     except Exception as e:
#         logging.error(f"❌ Failed to send data to Kafka topic {topic}: {e}")


# # ✅ Main Loop
# logging.info("🚀 Starting MBTA Data Pipeline")

# try:
#     while True:
#         for key, endpoint in ENDPOINTS.items():
#             fetch_and_produce(TOPICS[key], endpoint)

#         logging.info("⏳ Waiting for the next batch...")
#         time.sleep(30)

# except KeyboardInterrupt:
#     logging.info("🛑 Stopping MBTA Data Pipeline...")
#     producer.close()

import requests
import json
import time
import logging
from kafka import KafkaProducer

# ✅ MBTA API Configuration
MBTA_API_KEY = "6426e442cb644cae82e86def2e03ecb3"
MBTA_API_URL = "https://api-v3.mbta.com"

# ✅ Kafka Configuration
KAFKA_BROKER = "kafka:9092"
TOPICS = {
    "alerts": "mbta_alerts",
    "routes": "mbta_routes",
    "stops": "mbta_stops",
    "vehicles": "mbta_vehicles",
    "predictions": "mbta_predictions",
    "schedules": "mbta_schedules",
    "lines": "mbta_lines",
    "facilities": "mbta_facilities"
}

# ✅ Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Kafka Producer Setup
def create_kafka_producer():
    for _ in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                linger_ms=500,
                batch_size=16384,
                max_request_size=5000000,
                acks="all",
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            logging.info("✅ Kafka Producer connected successfully.")
            return producer
        except Exception as e:
            logging.error(f"❌ Kafka Producer connection failed: {e}")
            time.sleep(5)
    exit(1)

producer = create_kafka_producer()

# ✅ Static endpoints (excluding route-based ones)
STATIC_ENDPOINTS = {
    "alerts": f"/alerts?filter[activity]=ALL&api_key={MBTA_API_KEY}",
    "routes": f"/routes?api_key={MBTA_API_KEY}",
    "stops": f"/stops?api_key={MBTA_API_KEY}",
    "vehicles": f"/vehicles?api_key={MBTA_API_KEY}",
    "lines": f"/lines?api_key={MBTA_API_KEY}",
    "facilities": f"/facilities?api_key={MBTA_API_KEY}"
}

# ✅ Chunk large data
def chunk_records(data, chunk_size=500):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

# ✅ Fetch and send to Kafka
def fetch_and_produce(topic, endpoint):
    url = f"{MBTA_API_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("data"):
            logging.warning(f"⚠️ No data returned from {endpoint}")
            return

        payload = data["data"]
        size_kb = len(json.dumps(payload).encode("utf-8")) / 1024
        logging.info(f"📦 Payload size for {topic}: {size_kb:.2f} KB")

        if size_kb > 1000:
            logging.warning(f"⚠️ Splitting large payload into chunks for topic {topic}...")
            for chunk in chunk_records(payload):
                producer.send(topic, chunk)
                producer.flush()
        else:
            producer.send(topic, payload)
            producer.flush()

        logging.info(f"✅ Data sent to Kafka topic: {topic} ({len(payload)} records)")
    except Exception as e:
        logging.error(f"❌ Failed fetching/sending for {topic}: {e}")

# ✅ Get route IDs
def fetch_all_route_ids():
    try:
        url = f"{MBTA_API_URL}/routes?api_key={MBTA_API_KEY}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return [r["id"] for r in res.json()["data"]]
    except Exception as e:
        logging.error(f"❌ Error fetching route IDs: {e}")
        return []

# ✅ Main loop
logging.info("🚀 Starting MBTA Data Pipeline...")

try:
    while True:
        # Step 1: Static endpoints
        for key, endpoint in STATIC_ENDPOINTS.items():
            fetch_and_produce(TOPICS[key], endpoint)

        # Step 2: Dynamic per-route endpoints
        route_ids = fetch_all_route_ids()
        for route_id in route_ids:
            pred_ep = f"/predictions?filter[route]={route_id}&include=stop,trip,vehicle&api_key={MBTA_API_KEY}"
            sched_ep = f"/schedules?filter[route]={route_id}&api_key={MBTA_API_KEY}"
            fetch_and_produce(TOPICS["predictions"], pred_ep)
            fetch_and_produce(TOPICS["schedules"], sched_ep)
            time.sleep(0.5)  # Rate limit guard

        logging.info("⏳ Waiting for the next batch...")
        time.sleep(30)

except KeyboardInterrupt:
    logging.info("🛑 Stopping MBTA Data Pipeline...")
    producer.close()
