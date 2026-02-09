import os

def generate_slurm_conf(priority=False):
    conf = """ClusterName=user_scaling
AuthType=auth/none
SlurmUser=slurm
SlurmdUser=root
ControlMachine=localhost
ControlAddr=localhost
ReturnToService=1
MessageTimeout=60
JobRequeue=0
JobCredentialPrivateKey=/home/slurm/work/tutorials/user_scaling/etc/slurm.key
JobCredentialPublicCertificate=/home/slurm/work/tutorials/user_scaling/etc/slurm.cert
SlurmdParameters=config_overrides
ProctrackType=proctrack/pgid
SwitchType=switch/none
TopologyPlugin=topology/tree
TaskPlugin=task/none
FirstJobId=1001
UsePAM=0
GresTypes=gpu

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
SlurmSchedLogFile=/home/slurm/work/tutorials/user_scaling/log/sched.log
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory,CR_CORE_DEFAULT_DIST_BLOCK
EnforcePartLimits=YES

# LOGGING
SlurmctldDebug=info
SlurmdDebug=info
DebugFlags=Backfill
SlurmSchedLogLevel=1
SlurmctldLogFile=/home/slurm/work/tutorials/user_scaling/log/slurmctld.log
SlurmdLogFile=/home/slurm/work/tutorials/user_scaling/log/slurmd.log
SlurmdSpoolDir=/home/slurm/work/tutorials/user_scaling/var/spool
StateSaveLocation=/home/slurm/work/tutorials/user_scaling/var/state
JobCompType=jobcomp/filetxt
JobCompLoc=/home/slurm/work/tutorials/user_scaling/log/jobcomp.log

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

# NODES
NodeName=DEFAULT RealMemory=32000 Procs=8 Sockets=1 CoresPerSocket=8 ThreadsPerCore=1
NodeName=N[1-2] State=UNKNOWN

# PARTITIONS
PartitionName=normal Nodes=N[1-2] Default=YES DefMemPerCPU=1000 MaxTime=INFINITE State=UP
"""
    if priority:
        conf += """
PriorityType=priority/multifactor
PriorityDecayHalfLife=0-4
PriorityFavorSmall=YES
PriorityWeightFairshare=5000
PriorityWeightAge=2000
PriorityWeightPartition=0
PriorityWeightJobSize=500
PriorityWeightQOS=0
PriorityMaxAge=0-5
"""
    else:
        # FIFO behavior using basic priority or multifactor with weights 0
        conf += """
PriorityType=priority/basic
# effectively FIFO based on submission time if no other factors
"""
    return conf

def generate_slurmdbd_conf():
    return """DbdHost=localhost
AuthType=auth/none
PidFile=/home/slurm/work/tutorials/user_scaling/var/slurmdbd.pid
LogFile=/home/slurm/work/tutorials/user_scaling/log/slurmdbd.log
StorageHost=localhost
StorageUser=slurm
StoragePass=slurm
SlurmUser=slurm
StorageLoc=slurmdb_user_scaling
"""

def generate_users_sim(num_users=120):
    content = "admin:1000:admin:1000\n"
    for i in range(1, num_users + 1):
        content += f"user{i}:{1000+i}:users:100\n"
    return content

def generate_sacctmgr_script(num_users=120):
    script = """# add/modify QOS
modify QOS set normal Priority=0
# add cluster
add cluster Name=user_scaling Fairshare=1 QOS=normal
# add accounts
add account name=account1 Fairshare=100
# add admin
add user name=admin DefaultAccount=account1 MaxSubmitJobs=1000 AdminLevel=Administrator
# add users
"""
    for i in range(1, num_users + 1):
        script += f"add user name=user{i} DefaultAccount=account1 MaxSubmitJobs=1000\n"

    script += """# add users to qos level
modify user set qoslevel="normal"
# check results
list associations format=Account,Cluster,User,Fairshare tree withd
"""
    return script

def main():
    base_dir = "tutorials/user_scaling/etc"
    os.makedirs(base_dir, exist_ok=True)

    with open(os.path.join(base_dir, "slurm.conf.priority"), "w") as f:
        f.write(generate_slurm_conf(priority=True))

    with open(os.path.join(base_dir, "slurm.conf.fifo"), "w") as f:
        f.write(generate_slurm_conf(priority=False))

    with open(os.path.join(base_dir, "slurmdbd.conf"), "w") as f:
        f.write(generate_slurmdbd_conf())

    with open(os.path.join(base_dir, "users.sim"), "w") as f:
        f.write(generate_users_sim())

    with open(os.path.join(base_dir, "sacctmgr.script"), "w") as f:
        f.write(generate_sacctmgr_script())

    # Copy key and cert from micro_cluster if they exist, or create empty ones
    # For simulation auth/none, they might not be strictly needed but referenced in config
    # We will create dummy files
    with open(os.path.join(base_dir, "slurm.key"), "w") as f:
        f.write("")
    with open(os.path.join(base_dir, "slurm.cert"), "w") as f:
        f.write("")

if __name__ == "__main__":
    main()
