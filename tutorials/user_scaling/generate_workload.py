import random
import os
import numpy as np

# Configuration from Python script
# BASE_CONFIG = { ... "jobs": { ... } ... }
# But we focus on user scaling experiment params

def generate_jobs_for_users(num_users):
    jobs = []
    jid = 1001

    # "jobs": {
    #     "users": 40,
    #     "jobs_per_user": (10, 30),
    #     "submit_window": (0, 800),
    #     "duration_mean": 120,
    #     "duration_std": 80,
    #     "duration_bounds": (10, 300),
    # },

    jobs_per_user_range = (10, 30)
    submit_window = (0, 800)
    duration_mean = 120
    duration_std = 80
    duration_bounds = (10, 300)

    for u in range(1, num_users + 1):
        num_jobs = random.randint(*jobs_per_user_range)
        for _ in range(num_jobs):
            dur = np.clip(
                np.random.normal(duration_mean, duration_std),
                *duration_bounds
            )
            submit_time = random.uniform(*submit_window)
            cores = 2 if dur > 120 else 1
            ram = random.uniform(1, 8) * 1024 # Convert to MB for Slurm?
            # Wait, Slurm uses MB by default. 1-8 GB -> 1024-8192 MB.

            jobs.append({
                "job_id": jid,
                "user": f"user{u}",
                "cores": cores,
                "ram": int(ram),
                "duration": int(dur),
                "submit": submit_time
            })
            jid += 1

    return sorted(jobs, key=lambda j: j["submit"])

def write_events_file(jobs, filename):
    with open(filename, "w") as f:
        for job in jobs:
            # -dt <time> -e submit_batch_job | -J jobid_<id> -sim-walltime <dur> --uid=<user> -t <req_time> -n <cores> --mem=<mem> -A <account> -p <partition> -q <qos> pseudo.job

            # walltime in minutes for -t
            # -t 00:05:00
            # duration is in seconds.
            # -sim-walltime is the actual duration the job runs.
            # -t is the requested time limit. Let's set it slightly larger than duration or fixed.
            # The python script sets -t 00:01:00 for all? No, it sets duration.
            # In the micro_cluster example: -t 00:01:00.
            # Let's set -t to 10 minutes (600s) to be safe since max duration is 300s.

            dt = job["submit"]
            # Formatting dt to integer or float?
            # The example uses integers: -dt 0, -dt 1.
            # Slurmsim might support floats. "The arguments till the first pipe symbol (|) correspond to event time".
            # Let's check `read_trace` in `run_slurmsim.py`.
            # `dt = float(event_command[event_command.index("-dt") + 1])`
            # So floats are supported.

            line = f"-dt {dt:.2f} -e submit_batch_job | -J jobid_{job['job_id']} -sim-walltime {job['duration']} --uid={job['user']} -t 00:10:00 -n {job['cores']} --mem={job['ram']} -A account1 -p normal -q normal pseudo.job\n"
            f.write(line)

def main():
    user_counts = [10, 20, 40, 80, 120]
    base_dir = "tutorials/user_scaling/workload"
    os.makedirs(base_dir, exist_ok=True)

    # Set seed for reproducibility
    random.seed(42)
    np.random.seed(42)

    for n in user_counts:
        jobs = generate_jobs_for_users(n)
        filename = os.path.join(base_dir, f"jobs_{n}users.events")
        write_events_file(jobs, filename)
        print(f"Generated {filename} with {len(jobs)} jobs.")

if __name__ == "__main__":
    main()
