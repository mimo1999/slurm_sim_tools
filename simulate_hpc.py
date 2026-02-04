#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import random
import csv
from datetime import datetime
import time

# Defaults
DEFAULT_NUM_USERS = 5
DEFAULT_NUM_NODES = 10
DEFAULT_NODE_CAPACITY = 12
DEFAULT_PRIO_FAIRSHARE = 50000
DEFAULT_PRIO_AGE = 50000
DEFAULT_PRIO_SIZE = 200000
DEFAULT_SIM_DIR = os.path.abspath("simulation_run")

def setup_directories(sim_dir):
    if os.path.exists(sim_dir):
        shutil.rmtree(sim_dir)
    os.makedirs(sim_dir)
    os.makedirs(os.path.join(sim_dir, "etc"))
    os.makedirs(os.path.join(sim_dir, "workload"))
    os.makedirs(os.path.join(sim_dir, "log"))
    os.makedirs(os.path.join(sim_dir, "var", "spool"))
    os.makedirs(os.path.join(sim_dir, "var", "state"))
    os.makedirs(os.path.join(sim_dir, "results"))

    # Copy keys from tutorial if they exist, otherwise we might need to generate them or point to them
    # Assuming we are running in the repo root
    tutorial_etc = "tutorials/micro_cluster/etc"
    if os.path.exists(tutorial_etc):
        try:
            shutil.copy(os.path.join(tutorial_etc, "slurm.key"), os.path.join(sim_dir, "etc"))
            shutil.copy(os.path.join(tutorial_etc, "slurm.cert"), os.path.join(sim_dir, "etc"))
            shutil.copy(os.path.join(tutorial_etc, "topology.conf"), os.path.join(sim_dir, "etc"))
            shutil.copy(os.path.join(tutorial_etc, "gres.conf"), os.path.join(sim_dir, "etc"))
        except FileNotFoundError:
             print("Warning: Some tutorial files missing.")
    else:
        print(f"Warning: {tutorial_etc} not found. Keys might be missing.")

def generate_slurm_conf(sim_dir, args):
    conf_path = os.path.join(sim_dir, "etc", "slurm.conf")

    # Preemption settings
    preempt_type = ""
    preempt_mode = ""
    if args.preemption:
        preempt_type = "PreemptType=preempt/qos"
        preempt_mode = "PreemptMode=CANCEL"

    # Node definitions
    node_lines = []
    # e.g. NodeName=n[1-10] Procs=12 Sockets=2 CoresPerSocket=6 ThreadsPerCore=1 Feature=IB,CPU-N
    node_lines.append(f"NodeName=n[1-{args.num_nodes}] Procs={args.node_capacity} Sockets=1 CoresPerSocket={args.node_capacity} ThreadsPerCore=1 State=UNKNOWN")

    partition_lines = []
    partition_lines.append(f"PartitionName=normal Nodes=n[1-{args.num_nodes}] Default=YES MaxTime=INFINITE State=UP")

    content = f"""
ClusterName=micro
AuthType=auth/none
SlurmUser={os.environ.get('USER', 'slurm')}
SlurmdUser=root
ControlMachine=localhost
ControlAddr=localhost
ReturnToService=1
MessageTimeout=60
JobRequeue=0

JobCredentialPrivateKey={sim_dir}/etc/slurm.key
JobCredentialPublicCertificate={sim_dir}/etc/slurm.cert

SlurmdParameters=config_overrides
ProctrackType=proctrack/pgid
SwitchType=switch/none
TopologyPlugin=topology/tree
TaskPlugin=task/none

FirstJobId=1001

# TIMERS
SlurmctldTimeout=300
SlurmdTimeout=300
InactiveLimit=0
MinJobAge=300
KillWait=30
Waittime=0

# SCHEDULING
SchedulerType=sched/backfill
SchedulerParameters=bf_max_job_user=200,bf_window=1440,bf_interval=30,bf_max_time=30,sched_interval=60,bf_max_job_test=1200,default_queue_depth=1200,bf_continue
FairShareDampeningFactor=5
SlurmSchedLogFile={sim_dir}/log/sched.log
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory,CR_CORE_DEFAULT_DIST_BLOCK
PriorityType=priority/multifactor
PriorityDecayHalfLife=0-4
PriorityFavorSmall=NO
PriorityWeightFairshare={args.priority_fairshare}
PriorityWeightAge={args.priority_age}
PriorityWeightPartition=1000000
PriorityWeightJobSize={args.priority_size}
PriorityWeightQOS=20000
PriorityMaxAge=0-5
EnforcePartLimits=YES

# LOGGING
SlurmctldDebug=info
SlurmdDebug=info
DebugFlags=Backfill
SlurmSchedLogLevel=1

SlurmctldLogFile={sim_dir}/log/slurmctld.log
SlurmdLogFile={sim_dir}/log/slurmd.log
SlurmdSpoolDir={sim_dir}/var/spool
StateSaveLocation={sim_dir}/var/state
JobCompType=jobcomp/filetxt
JobCompLoc={sim_dir}/log/jobcomp.log

# ACCOUNTING
JobAcctGatherType=jobacct_gather/linux
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageEnforce=associations,limits,qos
AccountingStoreFlags=job_comment
AccountingStorageHost=localhost
PropagateResourceLimits=NONE
VSizeFactor=0
KillOnBadExit=1

FrontEndName=localhost

# GENERATED NODES
{chr(10).join(node_lines)}

# GENERATED PARTITIONS
{chr(10).join(partition_lines)}

# PREEMPTION
{preempt_type}
{preempt_mode}
"""
    with open(conf_path, "w") as f:
        f.write(content)

    # Slurmdbd.conf
    dbd_content = f"""
DbdHost=localhost
AuthType=auth/none
PidFile={sim_dir}/var/slurmdbd.pid
LogFile={sim_dir}/log/slurmdbd.log
StorageHost=localhost
StorageUser={os.environ.get('USER', 'slurm')}
StoragePass=slurm
SlurmUser={os.environ.get('USER', 'slurm')}
StorageLoc=slurmdb_micro
"""
    with open(os.path.join(sim_dir, "etc", "slurmdbd.conf"), "w") as f:
        f.write(dbd_content)

    # sim.conf
    # TimeStart needs to be a float timestamp.
    # We can use a fixed past timestamp or current time.
    start_ts = 1641013200.0
    sim_content = f"""
TimeStart = {start_ts}
TimeStop = 0
SecondsBeforeFirstJob = 126
ClockScaling = 1.0
EventsFile = {sim_dir}/workload/job_trace.events
TimeAfterAllEventsDone = 10
FirstJobDelay = -0.32
CompJobDelay = 0.000
TimeLimitDelay = 0.000
"""
    with open(os.path.join(sim_dir, "etc", "sim.conf"), "w") as f:
        f.write(sim_content)

def generate_users_sim(sim_dir, num_users):
    users_path = os.path.join(sim_dir, "etc", "users.sim")
    with open(users_path, "w") as f:
        f.write("admin:1000:admin:1000\n")
        for i in range(1, num_users + 1):
            f.write(f"user{i}:{1000+i}:group1:1001\n")

def generate_sacctmgr_script(sim_dir, args):
    script_path = os.path.join(sim_dir, "etc", "sacctmgr.script")

    content = []
    content.append("modify QOS set normal Priority=0")
    if args.preemption:
        # Superuser QOS can preempt normal QOS
        content.append("add QOS Name=superuser Priority=1000 Preempt=normal")
    else:
        content.append("add QOS Name=superuser Priority=100")

    content.append("add cluster Name=micro Fairshare=1 QOS=normal,superuser")
    content.append("add account name=account1 Fairshare=100")

    # Admin user
    content.append("add user name=admin DefaultAccount=account1 MaxSubmitJobs=1000 AdminLevel=Administrator QOS=superuser")

    # Regular users
    for i in range(1, args.num_users + 1):
        content.append(f"add user name=user{i} DefaultAccount=account1 MaxSubmitJobs=1000 QOS=normal")

    content.append('modify user set qoslevel="normal,superuser"')
    content.append("list associations format=Account,Cluster,User,Fairshare tree withd")

    with open(script_path, "w") as f:
        f.write("\n".join(content))

def generate_workload(sim_dir, args):
    events_path = os.path.join(sim_dir, "workload", "job_trace.events")

    num_jobs = 100 # Default number of jobs to simulate

    with open(events_path, "w") as f:
        # Example format:
        # -dt 0 -e submit_batch_job | -J jobid_1001 -sim-walltime 60 --uid=user1 -t 00:01:00 -n 1 --ntasks-per-node=1 -A account1 -p normal -q normal pseudo.job

        job_id = 1001
        dt = 0

        for i in range(num_jobs):
            # Inter-arrival time.
            # -dt parameter in slurm simulator events file represents the absolute time offset
            # from the start of the simulation, not the delta from the previous job.
            # So we accumulate the time.
            dt += random.randint(0, 30)

            # Determine user
            if args.preemption and random.random() < 0.1: # 10% chance of superuser job
                user = "admin"
                qos = "superuser"
            else:
                user = f"user{random.randint(1, args.num_users)}"
                qos = "normal"

            # Job specs
            walltime_sec = random.randint(60, 3600) # 1 min to 1 hour
            walltime_fmt = "01:00:00" # Simplified request

            # Nodes needed
            nodes_needed = random.randint(1, min(args.num_nodes, 4))

            # Write event
            line = (f"-dt {dt} -e submit_batch_job | -J jobid_{job_id} "
                    f"-sim-walltime {walltime_sec} --uid={user} -t {walltime_fmt} "
                    f"-n {nodes_needed * args.node_capacity} --ntasks-per-node={args.node_capacity} "
                    f"-A account1 -p normal -q {qos} pseudo.job\n")
            f.write(line)
            job_id += 1

def run_simulation(sim_dir, args):
    print("Running simulation...")

    # Environment variables
    env = os.environ.copy()
    env["CLUS_DIR"] = sim_dir

    # Set path to local slurm installation
    script_dir = os.path.dirname(os.path.abspath(__file__))
    slurm_install_path = os.path.join(script_dir, "slurm_install")

    # slurmsim run_sim command
    # slurmsim -v run_sim -d -e <etc> -a <sacctmgr> -w <workload> -r <results> -dtstart 0

    # Find slurmsim executable
    # Assuming script is in repo root, and slurmsim is in bin/
    slurmsim_path = os.path.join(script_dir, "bin", "slurmsim")

    if not os.path.exists(slurmsim_path):
        # Fallback to PATH
        slurmsim_path = "slurmsim"

    cmd = [
        slurmsim_path, "-v", "run_sim", "-d",
        "-e", os.path.join(sim_dir, "etc"),
        "-a", os.path.join(sim_dir, "etc", "sacctmgr.script"),
        "-w", os.path.join(sim_dir, "workload", "job_trace.events"),
        "-r", os.path.join(sim_dir, "results"),
        "-dtstart", "0"
    ]

    if os.path.isdir(slurm_install_path):
        cmd.extend(["-s", slurm_install_path])

    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error running simulation: {e}")
        # Check if it was connection refused
        print("\nPossible Cause: Database connection failed.")
        print("Please ensure MariaDB/MySQL is running and accessible by 'slurm' user without password (or configured in slurmdbd.conf).")
        print("Since this script generates a local simulation environment, you might need a local MySQL server instance.")
        # sys.exit(1) # Continue to analysis just in case something was generated?

def analyze_results(sim_dir):
    acct_file = os.path.join(sim_dir, "results", "slurm_acct.out")
    if not os.path.exists(acct_file):
        print("No accounting file found. Simulation likely failed or produced no output.")
        return

    jobs = []
    try:
        with open(acct_file, "r") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                jobs.append(row)
    except Exception as e:
        print(f"Error reading results: {e}")
        return

    if not jobs:
        print("No jobs found in accounting.")
        return

    # Calculate metrics
    total_wait_time = 0.0
    total_turnaround_time = 0.0
    total_utilization_time = 0.0

    count = 0
    min_start = float('inf')
    max_end = 0.0

    for job in jobs:
        # Time format: 2022-01-01T05:01:14
        fmt = "%Y-%m-%dT%H:%M:%S"
        try:
            submit = datetime.strptime(job["Submit"], fmt).timestamp()
            start = datetime.strptime(job["Start"], fmt).timestamp()
            end = datetime.strptime(job["End"], fmt).timestamp()

            # Skip if start or end is 0 or invalid (e.g. cancelled before start)
            if start == 0 or end == 0:
                continue

            wait = start - submit
            turnaround = end - submit
            elapsed = end - start
            ncpus = int(job["NCPUS"])

            total_wait_time += wait
            total_turnaround_time += turnaround
            total_utilization_time += (elapsed * ncpus)

            if start < min_start:
                min_start = start
            if end > max_end:
                max_end = end

            count += 1
        except ValueError:
            continue

    if count == 0:
        print("No valid jobs to analyze.")
        return

    avg_wait = total_wait_time / count
    avg_turnaround = total_turnaround_time / count

    simulation_duration = max_end - min_start
    if simulation_duration > 0:
        # This is a rough utilization metric (CPU-seconds consumed)
        print(f"Total CPU-Seconds Consumed: {total_utilization_time:.2f}")
        print(f"Simulation Duration: {simulation_duration:.2f} seconds")

    print("-" * 30)
    print(f"Number of Jobs: {count}")
    print(f"Average Wait Time: {avg_wait:.2f} seconds")
    print(f"Average Turnaround Time: {avg_turnaround:.2f} seconds")


def main():
    parser = argparse.ArgumentParser(description="Simulate HPC system performance")
    parser.add_argument("--num-users", type=int, default=DEFAULT_NUM_USERS, help="Number of users")
    parser.add_argument("--num-nodes", type=int, default=DEFAULT_NUM_NODES, help="Number of nodes")
    parser.add_argument("--node-capacity", type=int, default=DEFAULT_NODE_CAPACITY, help="CPUs per node")
    parser.add_argument("--priority-fairshare", type=int, default=DEFAULT_PRIO_FAIRSHARE, help="Priority weight for fairshare")
    parser.add_argument("--priority-age", type=int, default=DEFAULT_PRIO_AGE, help="Priority weight for age")
    parser.add_argument("--priority-size", type=int, default=DEFAULT_PRIO_SIZE, help="Priority weight for job size")
    parser.add_argument("--preemption", action="store_true", help="Enable preemption for super user")

    args = parser.parse_args()

    sim_dir = DEFAULT_SIM_DIR
    print(f"Setting up simulation in {sim_dir}")

    setup_directories(sim_dir)
    generate_slurm_conf(sim_dir, args)
    generate_users_sim(sim_dir, args.num_users)
    generate_sacctmgr_script(sim_dir, args)
    generate_workload(sim_dir, args)

    run_simulation(sim_dir, args)
    analyze_results(sim_dir)

if __name__ == "__main__":
    main()
