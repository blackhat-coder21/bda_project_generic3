# evaluator_classification.py
import json
import csv
from collections import deque, defaultdict
from kafka import KafkaConsumer

# CapyMOA 0.11.0 imports that are stable
from capymoa.stream.generator import LEDGenerator
from capymoa.classifier import HoeffdingTree, HoeffdingAdaptiveTree, NaiveBayes
from capymoa.evaluation import ClassificationEvaluator, ClassificationWindowedEvaluator

# Try extra learners if present (won't crash if missing)
EXTRA_LEARNERS = {}
try:
    from capymoa.classifier import AdaptiveRandomForestClassifier
    EXTRA_LEARNERS["ARF"] = AdaptiveRandomForestClassifier
except Exception:
    pass

try:
    from capymoa.classifier import OnlineBagging
    EXTRA_LEARNERS["OB"] = OnlineBagging
except Exception:
    pass

# --- Kafka / Data configuration ---
KAFKA_TOPIC = "aqi-stream"
KAFKA_SERVER = "localhost:9092"
METRICS_FILE = "metrics_classification.csv"

# --- Build a valid MOA-backed stream just to supply instances/schema ---
generator = LEDGenerator()            # legal MOA Java stream
SCHEMA = generator.schema             # use its schema for learners/evaluators

# --- Learners ---
LEARNERS = {
    "HT": HoeffdingTree(schema=SCHEMA),
    "HAT": HoeffdingAdaptiveTree(schema=SCHEMA, random_seed=42),
    "NB": NaiveBayes(schema=SCHEMA),
}
for key, cls in EXTRA_LEARNERS.items():
    try:
        LEARNERS[key] = cls(schema=SCHEMA)
    except Exception:
        pass

# --- Evaluators (kept for reference/compat; we compute our own accurate metrics) ---
CAPY_EVALS_WIN = {name: ClassificationWindowedEvaluator(schema=SCHEMA, window_size=100)
                  for name in LEARNERS}
CAPY_EVALS_CUM = {name: ClassificationEvaluator(schema=SCHEMA)
                  for name in LEARNERS}

# --- Our own reliable metrics ---
WIN_SIZE = 200  # sliding window length
win_buffers = {name: deque(maxlen=WIN_SIZE) for name in LEARNERS}
cum_counts = defaultdict(lambda: {"correct": 0, "total": 0})

CSV_HEADER = ["instance"]
for name in LEARNERS:
    CSV_HEADER += [f"{name}_win_acc", f"{name}_cum_acc"]

def initialize_metrics_file():
    with open(METRICS_FILE, "w", newline="") as f:
        csv.writer(f).writerow(CSV_HEADER)
    print(f"📊 Logging classification metrics to {METRICS_FILE}")

def run_evaluator():
    # Kafka consumer (just triggers pacing; we use generator for valid MOA instances)
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=[KAFKA_SERVER],
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        print("✅ Kafka Consumer connected. Waiting for data...")
    except Exception as e:
        print(f"❌ Kafka connection error: {e}")
        return

    initialize_metrics_file()
    i = 0

    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)

        for _msg in consumer:
            # Produce one legal MOA instance per Kafka message
            try:
                instance = generator.next_instance()
            except Exception as e:
                print(f"⚠️ Instance generation error: {e}")
                continue

            row = {"instance": i}

            for name, learner in LEARNERS.items():
                # Prequential: predict (test) then update metrics, then train
                y_pred = learner.predict(instance)
                y_pred = int(y_pred) if y_pred is not None else 0
                y_true = instance.y_index

                # Update CapyMOA evals (kept for reference/compat)
                try:
                    CAPY_EVALS_WIN[name].update(y_true, y_pred)
                    CAPY_EVALS_CUM[name].update(y_true, y_pred)
                except Exception:
                    pass

                # Update our robust metrics
                correct = 1 if y_pred == y_true else 0
                win_buffers[name].append(correct)
                cum_counts[name]["correct"] += correct
                cum_counts[name]["total"] += 1

                # Train
                learner.train(instance)

                # Compute % metrics (safe)
                win_acc = (sum(win_buffers[name]) / len(win_buffers[name]) * 100.0) if len(win_buffers[name]) > 0 else 0.0
                ctot = cum_counts[name]["total"]
                cum_acc = (cum_counts[name]["correct"] / ctot * 100.0) if ctot > 0 else 0.0

                row[f"{name}_win_acc"] = f"{win_acc:.2f}"
                row[f"{name}_cum_acc"] = f"{cum_acc:.2f}"

            if i % 20 == 0:
                hat_win = row.get("HAT_win_acc", "0.00")
                print(f"🧩 Instance {i} | HAT Window Acc: {hat_win}")

            writer.writerow(row)
            i += 1

if __name__ == "__main__":
    run_evaluator()

