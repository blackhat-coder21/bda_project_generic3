import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

METRICS_FILE = 'metrics.csv'
PLOT_WINDOW = 500 # How many recent instances to show in the plot

def plot_live_metrics(i):
    """
    Called by FuncAnimation to read the latest data and redraw the plot.
    """
    if not os.path.exists(METRICS_FILE):
        return # Wait for file to be created
        
    try:
        data = pd.read_csv(METRICS_FILE)
    except pd.errors.EmptyDataError:
        return # Wait for data to be written

    if data.empty:
        return

    plt.cla() # Clear the previous plot
    
    # Find all columns that are windowed accuracies
    win_acc_cols = [col for col in data.columns if col.endswith('_win_acc')]
    
    # Get the last N data points
    data_window = data.tail(PLOT_WINDOW)

    # Plot each model's windowed accuracy
    for col in win_acc_cols:
        model_name = col.replace('_win_acc', '')
        plt.plot(data_window['instance'], data_window[col], label=f'{model_name} (Window)')

    # --- Formatting ---
    plt.title('Live Model Performance (Windowed Accuracy)')
    plt.xlabel('Instances')
    plt.ylabel('Accuracy')
    
    # Show the concept drift line
    if data_window['instance'].min() < 2000 and data_window['instance'].max() > 2000:
         plt.axvline(x=2000, color='r', linestyle='--', label='Concept Drift')

    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()

def main():
    print("Starting live visualizer...")
    print(f"Waiting for data from {METRICS_FILE}...")
    
    fig = plt.figure(figsize=(12, 7))
    # Call the 'plot_live_metrics' function every 1 second
    ani = FuncAnimation(fig, plot_live_metrics, interval=1000)
    plt.show()

if __name__ == "__main__":
    main()
