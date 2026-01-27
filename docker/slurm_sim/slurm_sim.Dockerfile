FROM jupyter/datascience-notebook:x86_64-2023-10-20

LABEL desc="UB Slurm simulator (rootless podman compatible)"

ARG NEW_NB_USER=slurm
ARG NEW_NB_UID=1000
ARG NEW_NB_GID=1000

ENV NB_USER=${NEW_NB_USER} \
    NB_UID=${NEW_NB_UID} \
    NB_GID=${NEW_NB_GID} \
    HOME=/home/${NEW_NB_USER} \
    DEBIAN_FRONTEND=noninteractive \
    XDG_RUNTIME_DIR=/tmp/runtime-${NEW_NB_USER}

USER root

# ---- base packages (NO services) ----
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      git \
      vim \
      sudo \
      wget \
      zstd \
      libzstd-dev \
      libssl-dev \
      libssh-dev \
      libyaml-dev \
      libjwt-dev \
      libdbus-1-dev \
      libmariadb-dev \
      libhdf5-dev \
      mariadb-server \
      mariadb-client \
      openssh-client \
      default-jre \
      x11-apps \
      libswt-gtk-4-jni \
      file \
      procps \
      psmisc \
      python3-pandas \
      python3-pymysql \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---- user setup (rootless-safe) ----
RUN echo "DEBUG: NB_GID=${NB_GID}" && \
    userdel jovyan && \
    (groupdel 1000 || true) && \
    groupadd -g ${NB_GID} ${NB_USER} && \
    useradd -m -u ${NB_UID} -g ${NB_GID} -s /bin/bash ${NB_USER} && \
    echo "${NB_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${NB_USER}

# ---- runtime directories (user-owned) ----
RUN mkdir -p \
      /opt/slurm_sim \
      /opt/slurm_sim_tools \
      /opt/slurm_sim_bld \
      ${XDG_RUNTIME_DIR} \
    && chown -R ${NB_USER}:${NB_USER} \
      /opt \
      ${XDG_RUNTIME_DIR}

# ---- conda / jupyter fixes ----
RUN fix-permissions "${CONDA_DIR}"

USER ${NB_USER}
WORKDIR ${HOME}

# ---- python / r deps ----
RUN mamba install --yes \
      pymysql qgrid \
      r-plotly r-repr r-irdisplay r-pbdzmq \
      r-reticulate r-cowplot r-magrittr r-webshot2 \
    && mamba clean --all -f -y \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "${HOME}"

# ---- RStudio (no daemon start) ----
USER root
RUN wget -q https://download2.rstudio.org/server/jammy/amd64/rstudio-server-2023.12.1-402-amd64.deb && \
    dpkg -i rstudio-server-*-amd64.deb || true && \
    rm rstudio-server-*-amd64.deb && \
    mkdir -p /etc/R /etc/rstudio

RUN echo "rsession-which-r=/opt/conda/bin/R" >> /etc/rstudio/rserver.conf && \
    echo "auth-timeout-minutes=0" >> /etc/rstudio/rserver.conf

USER ${NB_USER}

# ---- copy slurm simulator ----
COPY --chown=${NB_USER}:${NB_USER} . /opt/slurm_sim_tools

# ---- build slurm simulator (NO services) ----
RUN mkdir -p /opt/slurm_sim_bld/opt && \
    cd /opt/slurm_sim_bld/opt && \
    /opt/slurm_sim_tools/slurm_simulator/configure \
      --prefix=/opt/slurm_sim \
      --disable-x11 \
      --enable-front-end \
      --with-hdf5=no \
      --enable-simulator \
      CFLAGS="-O3 -Wno-error=unused-variable -Wno-error=implicit-function-declaration" \
    && make -j$(nproc) \
    && make install

# ---- Setup Environment for Test Script ----
RUN ln -s /opt/conda/bin/Rscript /usr/local/bin/Rscript && \
    ln -s /opt /home/slurm/slurm_sim_ws && \
    ln -s /opt/slurm_sim /opt/slurm_opt && \
    ln -s /opt/slurm_sim_tools/docker/slurm_sim /install_files && \
    ln -s /opt/slurm_sim_tools/src/slurmsimtools/cp_slurm_conf_dir.py /opt/slurm_sim_tools/src/cp_slurm_conf_dir.py && \
    chmod +x /opt/slurm_sim_tools/docker/slurm_sim/*.sh /opt/slurm_sim_tools/docker/slurm_sim/*.py && \
    chmod +x /opt/slurm_sim_tools/src/slurmsimtools/cp_slurm_conf_dir.py && \
    env PATH=$PATH:/opt/conda/bin Rscript -e 'install.packages("/opt/slurm_sim_tools/src/RSlurmSimTools", repos = NULL, type="source")'

ENV PATH="/opt/slurm_sim_tools/bin:$PATH" \
    PYTHONPATH="/opt/slurm_sim_tools/src:$PYTHONPATH"

EXPOSE 8888 8787
