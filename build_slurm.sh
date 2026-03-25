#!/bin/bash
set -e
ROOT_DIR=$(pwd)
INSTALL_DIR="${ROOT_DIR}/slurm_install"

echo "Building Slurm Simulator..."
echo "Source: slurm_simulator"
echo "Install: ${INSTALL_DIR}"

if [ ! -d "slurm_simulator" ]; then
    echo "Error: slurm_simulator directory not found."
    exit 1
fi

cd slurm_simulator
./configure --prefix="${INSTALL_DIR}" --enable-simulator --enable-front-end --disable-munge --without-munge
make -j4
make install

echo "Build complete. Slurm installed to ${INSTALL_DIR}"
