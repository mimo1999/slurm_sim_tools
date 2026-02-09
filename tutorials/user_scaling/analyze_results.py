import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

RESULTS_DIR = "tutorials/user_scaling/results"
USER_COUNTS = [10, 20, 40, 80, 120]
SCHEDULERS = ["FIFO", "PRIORITY"]
TOTAL_CORES = 16  # 2 nodes * 8 cores

def parse_slurm_acct(filepath):
    # Read the file
    try:
        df = pd.read_csv(filepath, sep="|")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

    # Parse timestamps
    for col in ["Submit", "Start", "End"]:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Filter completed jobs
    df = df[df["State"] == "COMPLETED"]

    # Calculate metrics
    df["WaitTime"] = (df["Start"] - df["Submit"]).dt.total_seconds()
    df["TurnaroundTime"] = (df["End"] - df["Submit"]).dt.total_seconds()

    return df

def calculate_cpu_utilization(df, total_cores):
    if df.empty:
        return 0.0

    start_time = df["Submit"].min()
    end_time = df["End"].max()
    duration = (end_time - start_time).total_seconds()

    if duration <= 0:
        return 0.0

    # CPU busy time = sum(job_duration * job_cores)
    # job_duration = Elapsed? Or End - Start?
    # Elapsed is walltime.
    # NCPUS is allocated CPUs.

    # Convert Elapsed to seconds if it's string (HH:MM:SS) or just use End - Start
    job_duration = (df["End"] - df["Start"]).dt.total_seconds()
    core_busy_time = (job_duration * df["NCPUS"]).sum()

    utilization = core_busy_time / (duration * total_cores)
    return utilization

def main():
    results = {s: {"wait": [], "turnaround": [], "cpu": []} for s in SCHEDULERS}

    for u in USER_COUNTS:
        for s in SCHEDULERS:
            result_path = os.path.join(RESULTS_DIR, f"{s}_{u}users", "slurm_acct.out")

            if not os.path.exists(result_path):
                print(f"Warning: {result_path} not found.")
                results[s]["wait"].append(np.nan)
                results[s]["turnaround"].append(np.nan)
                results[s]["cpu"].append(np.nan)
                continue

            df = parse_slurm_acct(result_path)

            if df is not None and not df.empty:
                wait_time = df["WaitTime"].mean()
                turnaround_time = df["TurnaroundTime"].mean()
                cpu_util = calculate_cpu_utilization(df, TOTAL_CORES)

                results[s]["wait"].append(wait_time)
                results[s]["turnaround"].append(turnaround_time)
                results[s]["cpu"].append(cpu_util)
            else:
                results[s]["wait"].append(0)
                results[s]["turnaround"].append(0)
                results[s]["cpu"].append(0)

    # Plotting
    metrics = [("wait", "Mean Wait Time (s)"),
               ("turnaround", "Mean Turnaround Time (s)"),
               ("cpu", "CPU Utilization")]

    os.makedirs(os.path.join("tutorials/user_scaling", "plots"), exist_ok=True)

    for metric, ylabel in metrics:
        plt.figure()
        for s in SCHEDULERS:
            plt.plot(USER_COUNTS, results[s][metric], marker='o', label=s)

        plt.xlabel("Number of Users")
        plt.ylabel(ylabel)
        plt.title(f"{ylabel} vs Users")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join("tutorials/user_scaling", "plots", f"{metric}_vs_users.png"))
        print(f"Saved plot: {metric}_vs_users.png")

if __name__ == "__main__":
    main()
