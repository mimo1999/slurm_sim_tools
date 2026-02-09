#!/bin/bash
set -e

# This script is intended to be run inside the Docker container
# Mount point is assumed to be /home/slurm/work

BASE_DIR="/home/slurm/work/tutorials/user_scaling"
RESULTS_DIR="${BASE_DIR}/results"
mkdir -p ${RESULTS_DIR}

# Ensure bin is in PATH or use absolute path
export PATH="/home/slurm/work/bin:$PATH"
# Also need PYTHONPATH
export PYTHONPATH="/home/slurm/work/src:$PYTHONPATH"

USER_COUNTS="10 20 40 80 120"
SCHEDULERS="FIFO PRIORITY"

for users in $USER_COUNTS; do
    for sched in $SCHEDULERS; do
        echo "Running simulation for Users=${users}, Scheduler=${sched}"

        # Prepare slurm.conf
        if [ "$sched" == "FIFO" ]; then
            cp ${BASE_DIR}/etc/slurm.conf.fifo ${BASE_DIR}/etc/slurm.conf
        else
            cp ${BASE_DIR}/etc/slurm.conf.priority ${BASE_DIR}/etc/slurm.conf
        fi

        # Define run parameters
        WORKLOAD="${BASE_DIR}/workload/jobs_${users}users.events"
        RESULT_PATH="${RESULTS_DIR}/${sched}_${users}users"

        # Run simulation
        # Using slurmsim from the mounted volume (repo code)

        slurmsim -v run_sim -d \
            -e ${BASE_DIR}/etc \
            -a ${BASE_DIR}/etc/sacctmgr.script \
            -w ${WORKLOAD} \
            -r ${RESULT_PATH} \
            -dtstart 30

        echo "Finished simulation for Users=${users}, Scheduler=${sched}"
    done
done

echo "All simulations completed."
