import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Configuration ---
LOG_FILE = os.path.join("data_logs", "evaluation_metrics.csv")
DRIFT_POINT = 178 # The end of the first pass of the wine dataset
WINDOW_SIZE = 50  # Must match the new window size in the consumer

# --- 1. Load Data ---
try:
    df = pd.read_csv(LOG_FILE)
except FileNotFoundError:
    print(f"Error: Log file not found at {LOG_FILE}")
    print("Please run the consumer_evaluator.py script first to generate logs.")
    exit(1)

if df.empty:
    print("Log file is empty. No data to plot.")
    exit(1)

print(f"Loaded {len(df)} records from {LOG_FILE}")
model_names = df['model_name'].unique()

# --- 2. Create Plots ---
plt.style.use('seaborn-v0_8-whitegrid')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), sharex=True)

# --- Plot 1: Windowed Accuracy ---
ax1.set_title(f"Windowed Accuracy (Window Size = {WINDOW_SIZE})", fontsize=16)
ax1.set_ylabel("Accuracy")

for model in model_names:
    model_df = df[df['model_name'] == model]
    ax1.plot(model_df['instance'], model_df['windowed_accuracy'], label=model, lw=2)

# Add a vertical line to show where the "drift" (stream restart) occurred
ax1.axvline(x=DRIFT_POINT, color='r', linestyle='--', lw=2, label=f'Stream Restart at {DRIFT_POINT}')
ax1.legend(loc='lower left')
ax1.grid(True)


# --- Plot 2: Cumulative Accuracy ---
ax2.set_title("Cumulative Accuracy (Overall)", fontsize=16)
ax2.set_xlabel("Instance Number")
ax2.set_ylabel("Accuracy")

for model in model_names:
    model_df = df[df['model_name'] == model]
    ax2.plot(model_df['instance'], model_df['cumulative_accuracy'], label=model, lw=2)

ax2.axvline(x=DRIFT_POINT, color='r', linestyle='--', lw=2, label=f'Stream Restart at {DRIFT_POINT}')
ax2.legend(loc='lower left')
ax2.grid(True)


# --- Show Plot ---
plt.suptitle("CapyMOA Evaluation (Wine Dataset Stream)", fontsize=20, y=1.02)
plt.tight_layout()
plt.show()

print("Plot displayed. Close the plot window to exit.")
