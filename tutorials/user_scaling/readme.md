# User Scaling Experiment

This tutorial replicates the user scaling experiment where we scale the number of users from 10 to 120 and compare FIFO vs Priority scheduling.

## Directory Structure

- `etc/`: Configuration files (generated).
- `workload/`: Workload traces (generated).
- `results/`: Simulation results (created at runtime).
- `plots/`: Generated plots (created after analysis).

## Usage

### 1. Generate Configuration and Workload

Run the generation scripts to populate `etc/` and `workload/`.

```bash
python3 generate_config.py
python3 generate_workload.py
```

### 2. Run Simulation

The simulation requires the Slurm Simulator Docker image (`nsimakov/slurm_sim:v3.0`).
Use the provided `launch_docker.sh` script to run the experiment inside the container.

```bash
bash launch_docker.sh
```

This script will:
- Mount the current repository to the container.
- Execute `run_experiment.sh` inside the container.
- Run simulations for user counts [10, 20, 40, 80, 120] and schedulers [FIFO, PRIORITY].
- Store results in `results/`.

### 3. Analyze Results

Run the analysis script to generate plots.

```bash
python3 analyze_results.py
```

This will produce plots in the `plots/` directory:
- `wait_vs_users.png`
- `turnaround_vs_users.png`
- `cpu_vs_users.png`

## Experiment Details

- **Cluster**: 2 Nodes (N1, N2), 8 Cores, 32GB RAM each.
- **Workload**:
    - Users: 10, 20, 40, 80, 120.
    - Jobs per user: 10-30.
    - Duration: Mean 120s, Std 80s.
- **Schedulers**:
    - **FIFO**: Basic priority.
    - **Priority**: Multifactor with weights:
        - Age: 2000
        - Fairshare: 5000
        - JobSize: 500 (FavorSmall=YES)
