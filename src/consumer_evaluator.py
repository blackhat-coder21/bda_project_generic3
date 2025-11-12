import json
import csv
import os
from kafka import KafkaConsumer
import numpy as np

# --- Import CapyMOA Learners ---
from capymoa.classifier import (
    HoeffdingTree,
    HoeffdingAdaptiveTree,
    AdaptiveRandomForestClassifier,
    NaiveBayes,
    OnlineBagging
)
# --- Import CapyMOA Evaluators ---
from capymoa.evaluation import (
    ClassificationEvaluator,
    ClassificationWindowedEvaluator
)
# --- Import Schema and LabeledInstance ---
from capymoa.stream import Schema 
# We no longer need LabeledInstance or Instance

# --- Configuration ---
KAFKA_TOPIC = "capymoa_stream"
KAFKA_BROKER = "localhost:9092"
LOG_DIR = "data_logs"
LOG_FILE = os.path.join(LOG_DIR, "evaluation_metrics.csv")
WINDOW_SIZE = 50  # Smaller window for a smaller dataset
LOG_FREQUENCY = 25 # Log more frequently
TOTAL_INSTANCES = 356 # 178 * 2

# --- 1. Create Log Directory and File ---
os.makedirs(LOG_DIR, exist_ok=True)
csv_header = ["instance", "model_name", "cumulative_accuracy", "windowed_accuracy"]
log_file = open(LOG_FILE, 'w', newline='')
writer = csv.writer(log_file)
writer.writerow(csv_header)
print(f"✅ Logging metrics to {LOG_FILE}")

# --- 2. Define Schema and Initialize Learners ---
# FIX: Use Schema.from_custom (this is the correct constructor)
wine_feature_names = [f"feature_{i}" for i in range(13)]
wine_class_labels = ["class_0", "class_1", "class_2"]

stream_schema = Schema.from_custom(
    feature_names=wine_feature_names,
    values_for_class_label=wine_class_labels
)
print("✅ Defined schema for Wine dataset (13 features, 3 classes).")

learners = {
    "HoeffdingTree": HoeffdingTree(schema=stream_schema),
    "HAT": HoeffdingAdaptiveTree(schema=stream_schema),
    "ARF": AdaptiveRandomForestClassifier(schema=stream_schema, random_seed=1),
    "NaiveBayes": NaiveBayes(schema=stream_schema),
    "OnlineBagging": OnlineBagging(schema=stream_schema, random_seed=1)
}
print(f"✅ Initialized {len(learners)} models: {list(learners.keys())}")

# --- 3. Initialize Evaluators ---
evaluators = {
    name: {
        "cumulative": ClassificationEvaluator(schema=stream_schema),
        "windowed": ClassificationWindowedEvaluator(schema=stream_schema, window_size=WINDOW_SIZE)
    }
    for name in learners.keys()
}

# --- 4. Set up Kafka Consumer ---
try:
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    print("✅ Kafka Consumer connected. Waiting for messages...")
except Exception as e:
    print(f"❌ Error connecting to Kafka: {e}")
    log_file.close()
    exit(1)

# --- 5. Main Prequential (Test-then-Train) Loop ---
try:
    instance_count = 0
    for message in consumer:
        data = message.value
        
        # --- 5a. Convert JSON data back to (x, y) ---
        # We need a numpy array with float32 for the wrappers
        x_array = np.array(data['features'], dtype=np.float32)
        y_true = data['label'] # This is an integer (0, 1, or 2)
        instance_id = data['instance_id']

        # --- 5b. Iterate through each learner ---
        # FIX: Revert to using the high-level wrappers .predict() and .train()
        # This lets CapyMOA handle the Java Instance creation.
        for name, learner in learners.items():
            
            # 1. TEST (Predict): Get prediction *before* training
            # 'predict()' takes the float32 numpy array and returns a numpy array
            y_pred_array = learner.predict(x_array)
            # We want the first (and only) prediction
            y_pred = int(y_pred_array[0]) # Cast to int
            
            # 2. UPDATE EVALUATORS
            eval_pair = evaluators[name]
            eval_pair["cumulative"].update(y_true, y_pred)
            eval_pair["windowed"].update(y_true, y_pred)
            
            # 3. TRAIN: Update the model with the new instance
            # 'train()' takes the float32 numpy array and the integer label
            learner.train(x_array, y_true)

        instance_count += 1
        
        # --- 5c. Log metrics periodically ---
        if instance_count % LOG_FREQUENCY == 0:
            print(f"\n--- Instance {instance_count} ---")
            for name in learners.keys():
                cum_acc = evaluators[name]["cumulative"].get_accuracy()
                win_acc = evaluators[name]["windowed"].get_accuracy()
                
                print(f"  {name}:  Cum.Acc = {cum_acc:.4f} | Win.Acc = {win_acc:.4f}")
                writer.writerow([instance_count, name, cum_acc, win_acc])
                
        # Stop after processing all instances
        if instance_count >= TOTAL_INSTANCES:
             print(f"✅ Processed {TOTAL_INSTANCES} instances. Stopping consumer.")
             break

except KeyboardInterrupt:
    print("\n🛑 Interrupted by user.")
except Exception as e:
    print(f"❌ Error in consumer loop: {e}")
finally:
    consumer.close()
    log_file.close()
    print("✅ Kafka Consumer and log file closed safely.")
