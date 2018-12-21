# lvm_snaphot.py
This script can create and remove the LVM snapshot. It can also add a temporary file into an LVM volume group, 
to provide additional space for snapshot. Script also performs many checks before doing 
serious things, and tries to carefully cleanup everything or at least fail fast if something goes wrong.

## Typical usage
Command lines listed below cover the most typical cases. For other cases, refer to script help output.
### Getting help output
```bash
lvm_snaphot.py -h
```
### Creating snapshot
* To create LVM snapshot using free space at LVM volume group and mount the snapshot to the mountpoint:
```bash
lvm_snaphot.py --source-lvm-vg lvm_server_vg --source-lvm-lv system \
  --lvm-snapshot-name snap1 --mountpoint /media/system_snapshot \
  snapshot-mount
```
* To: 
  * create a temporary file at /media/other_partition/tmp_space.tmp
    * default temporary file size is 4GB, use the `--lvm-volume-size-mb` option to customize it
    * by default, `dd` tool is used to create a file. Check the `--use-fallocate` option that is better in many cases  
  * mount the temporary file to the loop device /dev/loop5
  * add this loop device as a physical volume to the LVM group
  * use the united free space of LVM volume to create an LVM snapshot
  * mount the snapshot to the mountpoint
```bash
lvm_snaphot.py --source-lvm-vg lvm_server_vg --source-lvm-lv system \
                 --lvm-snapshot-name snap1 --mountpoint /media/system_snapshot \
                 --lvm-snapshot-tmp-file /media/other_partition/tmp_space.tmp --loop-device /dev/loop5 \
                 snapshot-mount
```

### Removing snapshot
When removing a snapshot, always specify all options passed to `snapshot-mount`. That is required for proper
cleanup in non-trivial cases (like allocated temporary file).
* To unmount the snapshot from the mountpoint, and remove both mountpoint and snapshot:
```bash
lvm_snaphot.py --source-lvm-vg lvm_server_vg --source-lvm-lv system \
  --lvm-snapshot-name snap1 --mountpoint /media/system_snapshot \
  --remove-mountpoint snapshot-unmount
```
* To:
  * unmount the snapshot from the mountpoint
  * remove the mountpoint /media/system_snapshot
  * remove snapshot from an LVM group
  * remove the loop device /dev/loop5 from an LVM group
  * unmount the temporary file from the loop device /dev/loop5
  * remove the temporary file /media/other_partition/tmp_space.tmp
```bash
lvm_snaphot.py --source-lvm-vg lvm_server_vg --source-lvm-lv system \
                 --lvm-snapshot-name snap1 --mountpoint /media/system_snapshot \
                 --lvm-snapshot-tmp-file /media/other_partition/tmp_space.tmp --loop-device /dev/loop5 \
                 --remove-mountpoint snapshot-unmount
``` 
### Template of a backup script that uses LVM snapshots
```bash
#!/usr/bin/env bash
# Path to a local clone of backup-lvm-fsa-snapshot repository
PATH_TO_BACKUP_TOOLS_REPO="$1"

# Mountpoint where filesystem from a snapshot is mounted
SYSTEM_SNAPSHOT="/media/system_snapshot_mountpoint"
LVM_SNAPSHOT_MOUNT_OPTS="--source-lvm-vg lvm_server_vg --source-lvm-lv system --lvm-snapshot-name snap1 --mountpoint ${SYSTEM_SNAPSHOT}"
LVM_SNAPSHOT_UNMOUNT_OPTS="$LVM_SNAPSHOT_MOUNT_OPTS --remove-mountpoint"

echo "Creating snapshot of LVM partition"

set -e
python3 ${PATH_TO_BACKUP_TOOLS_REPO}/scripts/lvm_snaphot.py ${LVM_SNAPSHOT_MOUNT_OPTS}  snapshot-mount

# HERE: Perform the backup of files available at $SYSTEM_SNAPSHOT. Make sure you script exit code correctly 
# and snapshot-unmount action is always executed

echo "Removing snapshot of LVM partition"
${PATH_TO_BACKUP_TOOLS_REPO}/scripts/lvm_snaphot.py ${LVM_SNAPSHOT_UNMOUNT_OPTS} --remove-mountpoint snapshot-unmount

set +e
```
