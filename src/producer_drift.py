# producer_drift.py
import json
import random
import time
from kafka import KafkaProducer

# --- MODIFICATION ---
TOPIC = "aqi-drift-stream" # Changed from "aqi-stream"
# --- END MODIFICATION ---

SERVER = "localhost:90_92"
RATE = 500  # msgs per second (approx)
DRIFT_AT = 10000

CLASSES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]

def permute_labels(cls):
    p = cls[:]
    random.shuffle(p)
    return p

def generate_sample(tick, labels_map):
    # (Rest of the file is identical to what you provided)
    # ...
    sample = {
        "PM2.5": random.uniform(0, 300),
        "PM10": random.uniform(0, 300),
        "NO": random.uniform(0, 100),
        "NO2": random.uniform(0, 100),
        "NH3": random.uniform(0, 100),
        "CO": random.uniform(0, 10),
        "SO2": random.uniform(0, 100),
        "O3": random.uniform(0, 100),
        "Benzene": random.uniform(0, 50),
        "Toluene": random.uniform(0, 50),
        "Xylene": random.uniform(0, 50),
    }
    raw_idx = int((sample["PM2.5"] + sample["PM10"]) // 100) % len(CLASSES)
    sample["AQI_Bucket"] = labels_map[raw_idx]
    return sample

if __name__ == "__main__":
    producer = KafkaProducer(bootstrap_servers=[SERVER],
                             value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    
    # --- MODIFICATION ---
    print(f"🚀 Drifted producer started… writing to topic '{TOPIC}'")
    # --- END MODIFICATION ---

    labels_map = CLASSES[:]  # initial mapping (no drift)
    i = 0
    last = time.time()

    try:
        while True:
            if i == DRIFT_AT:
                labels_map = permute_labels(CLASSES)
                print(f"⚡ Concept drift at {i}: permuted labels -> {labels_map}")
            if i == DRIFT_AT * 2:
                labels_map = ["Poor"] + [c for c in CLASSES if c != "Poor"]
                print(f"⚡ Concept drift at {i}: biased Poor -> {labels_map}")

            sample = generate_sample(i, labels_map)
            producer.send(TOPIC, sample)

            i += 1
            if RATE > 0:
                now = time.time()
                elapsed = now - last
                expected = i / RATE
                if expected > elapsed:
                    time.sleep(expected - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        producer.flush()
        producer.close()
        print("🛑 Producer stopped.")
