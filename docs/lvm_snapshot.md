# lvm_snaphot.py
This script can create and remove the LVM snapshot. 
<!-- TODO: --> Write description


##  What this script does

- Script also performs necessary checks (more then 20) before doing serious things, and tries to carefully cleanup things
 if previous script invocation failed.
  

<!-- TODO: -->
- Script installs fsarchiver or pigz package if it is required and not installed
- Script creates destination directory at --backup-dest-dir for storing backups 
if it does not exist 
- Script creates 4096 mb tmp file (use --snapshot-volume-size-mb to customize) 
in directory, specified via --lvm-snapshot-tmp-file-dir . 
If arg --tmp-dir-is-local is specified,
 file is created using fallocate call (fast, but applicable only to local filesystem). 
 Otherwise, if --tmp-dir-is-remote parameter is passed, temporary file is created 
 using dd. Alternatively, if --tmp-dir-is-lvm parameter is passed, creating temporary file 
 is skipped and lvm spare space is used.
- Then script creates a loop device on tmp file allocated earlier (if not --tmp-dir-is-lvm)
- Then (if not --tmp-dir-is-lvm) script creates an LVM physical volume for volume group specified via --source-lvm-volume-group.
 Physical volume is created on the loop device created beforehand.
- Then script creates an LVM snapshot for LVM logical volume specified via 
 --source-lvm-volume-group and --source-lvm-logical-volume options. Size of volume defaults to
4096 mb and can be customized via --snapshot-volume-size-mb. 
- Then script creates a dump of snapshot volume. Backup is created via fsarchiver. 
Backup is compressed, compression uses all available CPUs, compression levels 
(see http://www.fsarchiver.org/Compression) are defined using --compression-level
 parameter.
- every Sunday, a weekly dump is created. On other days a daily dump is created.
 Limits of weekly and daily dump files are managed separately and 
 are defined using --daily-backup-max-count and
 --weekly-backup-max-count properties. Oldest dump files that exceed this limit are deleted.
 E.g. 7 daily backups and 4 weekly backups mean that one has daily backups for the last week
 and weekly backups for the last month. 
- After backup is finished, script removes physical volume, loop device and tmp file created earlier.
- Then script removes old dumps (exceeding limits specified via --daily-backup-max-count 
 and --weekly-backup-max-count
 
 
## Typical usage examples

### Adding a temporary file to LVM volume to use as an additional storage
* Allocate a temporary file and mount it to a loop device. By default, a 4GB temporary file is allocated. Then, create 
snapshot of an LVM partition and mount it to mountpoint. 
```bash
lvm_snaphot.py --source-lvm-vg my_lvm_vg --source-lvm-lv system --lvm-snapshot-name snap1 \
    --mountpoint  /media/system_snapshot \
    --lvm-snapshot-tmp-file /media/other-partition/1.tmp --use-fallocate --loop-device /dev/loop5
```

* unmount the snapshot from a mountpoint and remove the snapshot and mountpoint directory
```bash
lvm_snaphot.py --source-lvm-vg my_lvm_vg --source-lvm-lv system --lvm-snapshot-name snap1 \
    --mountpoint  /media/system_snapshot \
    --lvm-snapshot-tmp-file /media/other-partition/1.tmp --use-fallocate --loop-device /dev/loop5 \
    --remove-mountpoint 
```