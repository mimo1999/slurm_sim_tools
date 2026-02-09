#!/bin/bash

# Determine repo root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
REPO_ROOT=$(dirname $(dirname "$SCRIPT_DIR"))

echo "Repo root: $REPO_ROOT"
echo "Script dir: $SCRIPT_DIR"

# Ensure directories are writable by the container user (likely uid 1000)
chmod -R 777 "${SCRIPT_DIR}"

# Mount repo root to /home/slurm/work
# Run as user slurm (assuming it exists in image)
docker run --rm \
    -v "${REPO_ROOT}:/home/slurm/work" \
    --user slurm \
    nsimakov/slurm_sim:v3.0 \
    bash /home/slurm/work/tutorials/user_scaling/run_experiment.sh
