# backup-lvm-fsa-snapshot
A set of scripts performing backups. Each script is focused on a single function and attempts to perform it well


## Compatibility
All scripts require Python version >= 3.5. All scripts are tested on Ubuntu 16.04/18.04 but should work on 
all recent Debian-based distributions, and maybe also on other Linux flavours.

# Included scripts
* [lvm_snapshot.py](https://github.com/Dmitriusan/backup-lvm-fsa-snapshot/blob/master/docs/lvm_snapshot.md)
* [manage_backups.py](https://github.com/Dmitriusan/backup-lvm-fsa-snapshot/blob/master/docs/manage_backups.md)

## Beware when doing system backups via LVM snapshot feature!
1. **Never** point backup archive file to the same partition that is being 
backed up. **Snapshot space will be overfilled.**
1. **Never** point tmp snaphot file destination (`--lvm-snapshot-tmp-file` argument of `lvm_snaphot.py` script) 
to the same partition that is being backed up. **Or entire filesystem will hang!!!**
1. **Never reboot computer without removing snapshot volume and physical volume 
pointing to loop device**. On next boot,
temporary loop device will not be available, and entire LVM volume group will
be marked as unreachable/unmountable, so operating system will fail
to boot. The latter said does not rely to snapshot volumes allocated on a spare
space of LVM partition.
1. If you did not follow advice 2. and rebooted while performing backup, 
you can fix everything by booting from live cd and running 
```
vgreduce --removemissing --force <your vg name>
```

# Example of bash script for Jenkins job for performing a backup
```bash
#!/usr/bin/env bash
# Current script dumps lvm system partition
#
# Usage: run_backup_script.sh /path/to/clone/of/this/repository/backup-lvm-fsa-snapshot

if [[ "$#" -ne 1 ]]; then
    echo "Illegal number of parameters"
    exit 1
fi

# Path to a local clone of backup-lvm-fsa-snapshot repository
PATH_TO_BACKUP_TOOLS_REPO="$1"

BACKUPS_DIR="/media/backups/auto/"

# Mountpoint where filesystem from a snapshot is mounted
SYSTEM_SNAPSHOT="/media/system_snapshot_mountpoint"
LVM_SNAPSHOT_MOUNT_OPTS="--source-lvm-vg lvm_server_vg --source-lvm-lv system --lvm-snapshot-name snap1 --mountpoint ${SYSTEM_SNAPSHOT}"
LVM_SNAPSHOT_UNMOUNT_OPTS="$LVM_SNAPSHOT_MOUNT_OPTS --remove-mountpoint"

BACKUP_AUTOCLEAN_SETTINGS="--daily-backups-max-count 5 --weekly-backups-max-count 3 --monthly-backups-max-count 2 --yearly-backups-max-count 0"
BACKUP_MGMT_SCRIPT="${PATH_TO_BACKUP_TOOLS_REPO}/scripts/manage_backups.py"
BACKUP_MGMT_SETTINGS="--backup-dest-dir "${BACKUPS_DIR}" --prefix system_dump --extension tar.gz"

set -e

BACKUP_FILE=$(${BACKUP_MGMT_SCRIPT} generate-name ${BACKUP_MGMT_SETTINGS})

echo "Creating snapshot of LVM partition"
python3 ${PATH_TO_BACKUP_TOOLS_REPO}/scripts/lvm_snaphot.py ${LVM_SNAPSHOT_MOUNT_OPTS}  snapshot-mount

set +e

/bin/tar cf - "${SYSTEM_SNAPSHOT}" | /usr/bin/pigz -5 > "${BACKUP_FILE}" && \
    ${BACKUP_MGMT_SCRIPT} auto-clean ${BACKUP_MGMT_SETTINGS} ${BACKUP_AUTOCLEAN_SETTINGS} || \
    ${BACKUP_MGMT_SCRIPT} remove-unsuccessful ${BACKUP_MGMT_SETTINGS} --remove-file "${BACKUP_FILE}" ; \
    (( exit_status = exit_status || $? ))

echo "Removing snapshot of LVM partition"
${PATH_TO_BACKUP_TOOLS_REPO}/scripts/lvm_snaphot.py ${LVM_SNAPSHOT_UNMOUNT_OPTS} --remove-mountpoint snapshot-unmount; \
    (( exit_status = exit_status || $? ))

exit ${exit_status}
```