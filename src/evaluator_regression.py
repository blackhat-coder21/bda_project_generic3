# evaluator_regression.py
import json
import csv
from math import sqrt
from collections import deque, defaultdict
from kafka import KafkaConsumer

# CapyMOA regressors (guarded)
REG_LEARNERS = {}
try:
    from capymoa.regressor import FIMTDD
    REG_LEARNERS["FIMTDD"] = FIMTDD
except Exception:
    pass
try:
    from capymoa.regressor import AdaptiveRandomForestRegressor
    REG_LEARNERS["ARFReg"] = AdaptiveRandomForestRegressor
except Exception:
    pass
try:
    from capymoa.regressor import OnlineBaggingRegressor
    REG_LEARNERS["OBReg"] = OnlineBaggingRegressor
except Exception:
    pass

if not REG_LEARNERS:
    print("⚠️ No regression learners available in your CapyMOA 0.11.0 install. Skipping.")
    exit(0)

# We still need a schema/instances; LEDGenerator is classification, but generates numeric X + y_index.
# We'll treat y_index as a numeric target (simulated regression). For real regression, switch to a proper reg stream if available in your env.
from capymoa.stream.generator import LEDGenerator
generator = LEDGenerator()
SCHEMA = generator.schema

# Kafka pacing
KAFKA_TOPIC = "aqi-stream"
KAFKA_SERVER = "localhost:9092"
METRICS_FILE = "metrics_regression.csv"

# Instantiate learners
LEARNERS = {name: cls(schema=SCHEMA) for name, cls in REG_LEARNERS.items()}

WIN_SIZE = 200
win_buffers = {name: deque(maxlen=WIN_SIZE) for name in LEARNERS}  # store absolute errors
cum_stats = defaultdict(lambda: {"sum_abs": 0.0, "sum_sq": 0.0, "n": 0})

CSV_HEADER = ["instance"]
for name in LEARNERS:
    CSV_HEADER += [f"{name}_win_mae", f"{name}_cum_mae", f"{name}_cum_rmse"]

def initialize_metrics_file():
    with open(METRICS_FILE, "w", newline="") as f:
        csv.writer(f).writerow(CSV_HEADER)
    print(f"📊 Logging regression metrics to {METRICS_FILE}")

def run_evaluator():
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=[KAFKA_SERVER],
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        print("✅ Kafka Consumer connected. Waiting for data (regression)...")
    except Exception as e:
        print(f"❌ Kafka connection error: {e}")
        return

    initialize_metrics_file()
    i = 0

    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)

        for _msg in consumer:
            try:
                instance = generator.next_instance()
                # Use the class index as a numeric target in this demo
                y_true = float(instance.y_index)
            except Exception as e:
                print(f"⚠️ Instance generation error: {e}")
                continue

            row = {"instance": i}

            for name, learner in LEARNERS.items():
                # predict
                y_pred = learner.predict(instance)  # CapyMOA returns scalar-ish
                y_pred = float(y_pred) if y_pred is not None else 0.0

                # update errors
                err = abs(y_pred - y_true)
                win_buffers[name].append(err)
                cum_stats[name]["sum_abs"] += err
                cum_stats[name]["sum_sq"] += (y_pred - y_true) ** 2
                cum_stats[name]["n"] += 1

                # train
                learner.train(instance)

                # metrics
                win_mae = (sum(win_buffers[name]) / len(win_buffers[name])) if len(win_buffers[name]) > 0 else 0.0
                n = cum_stats[name]["n"]
                cum_mae = (cum_stats[name]["sum_abs"] / n) if n > 0 else 0.0
                cum_rmse = sqrt(cum_stats[name]["sum_sq"] / n) if n > 0 else 0.0

                row[f"{name}_win_mae"] = f"{win_mae:.4f}"
                row[f"{name}_cum_mae"] = f"{cum_mae:.4f}"
                row[f"{name}_cum_rmse"] = f"{cum_rmse:.4f}"

            if i % 20 == 0:
                # pick any one learner to display
                k = next(iter(LEARNERS))
                print(f"📈 [Reg] Instance {i} | {k} win_MAE: {row[f'{k}_win_mae']}  cum_MAE: {row[f'{k}_cum_mae']}")

            writer.writerow(row)
            i += 1

if __name__ == "__main__":
    run_evaluator()

