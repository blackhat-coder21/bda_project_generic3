# producer.py
import kafka
from kafka import KafkaProducer
import pandas as pd
import json
import time
import random

KAFKA_TOPIC = 'aqi-stream'
KAFKA_SERVER = 'localhost:9092'
DATA_FILE = 'data/cleaned_aqi_data.csv'

# Concept Drift Simulation
DRIFT_POINT = 2000  # Start drift after 2000 instances
DRIFT_FEATURE = 'PM2.5' # Feature to modify
DRIFT_FACTOR = 3    # How much to multiply the feature by

def create_producer():
    """Creates and returns a KafkaProducer."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_SERVER],
            # Serialize (convert) values to JSON format
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Kafka Producer connected successfully.")
        return producer
    except kafka.errors.NoBrokersAvailable:
        print(f"Error: No Kafka brokers available at {KAFKA_SERVER}.")
        print("Please ensure your two Kafka terminals (Zookeeper, Server) are running.")
        exit(1)

def stream_data(producer):
    """
    Reads the cleaned CSV and streams it row by row to Kafka.
    """
    print(f"Loading data from {DATA_FILE}...")
    try:
        df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        print(f"Error: Cleaned data file not found at {DATA_FILE}")
        print("Please run 'python3 data_preprocessor.py' first.")
        return

    print(f"Starting to stream {len(df)} instances to topic '{KAFKA_TOPIC}'...")
    
    instance_count = 0
    # Loop forever to simulate a continuous stream
    while True:
        for i, row in df.iterrows():
            data_record = row.to_dict()
            
            # --- Concept Drift Simulation ---
            if instance_count > DRIFT_POINT:
                if (instance_count == DRIFT_POINT + 1):
                     print("-" * 30)
                     print(f"!!! CONCEPT DRIFT INITIATED AT INSTANCE {instance_count} !!!")
                     print(f"!!! Modifying '{DRIFT_FEATURE}' by a factor of {DRIFT_FACTOR} !!!")
                     print("-" * 30)
                
                # Apply the drift
                if DRIFT_FEATURE in data_record:
                    drift_value = data_record[DRIFT_FEATURE] * (DRIFT_FACTOR + random.random())
                    data_record[DRIFT_FEATURE] = drift_value
            
            # Send data to Kafka
            producer.send(KAFKA_TOPIC, data_record)
            print(f"Sent instance {instance_count}")
            instance_count += 1

            # Sleep to simulate a real-time feed (20 messages/sec)
            time.sleep(0.05) 

        print("Finished one pass of the dataset. Looping again...")

if __name__ == "__main__":
    producer = create_producer()
    if producer:
        stream_data(producer)
