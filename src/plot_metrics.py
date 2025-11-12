# plot_metrics.py
import time
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def live_plot(csv_path, metric_suffix="_win_acc", refresh=2.0):
    plt.ion()
    fig, ax = plt.subplots()
    last_len = 0

    while True:
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            time.sleep(refresh)
            continue

        ax.clear()
        if "instance" in df.columns:
            x = df["instance"].values
        else:
            x = range(len(df))

        # pick all columns ending with suffix
        cols = [c for c in df.columns if c.endswith(metric_suffix)]
        for c in cols:
            # many of our CSV fields are strings formatted like "87.32"
            try:
                y = pd.to_numeric(df[c], errors="coerce")
                ax.plot(x, y, label=c.replace(metric_suffix, ""))
            except Exception:
                pass

        ax.set_xlabel("Instance")
        ax.set_ylabel(metric_suffix.strip("_").upper())
        ax.legend(loc="best")
        ax.grid(True)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(refresh)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to metrics csv")
    ap.add_argument("--metric", default="_win_acc", help="Suffix to plot (e.g. _win_acc, _cum_acc, _win_mae)")
    ap.add_argument("--refresh", type=float, default=2.0, help="Seconds between refresh")
    args = ap.parse_args()
    live_plot(args.csv, metric_suffix=args.metric, refresh=args.refresh)

