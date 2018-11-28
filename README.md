# backup-lvm-fsa-snapshot
A set of scripts performing backups. Each script is focused on a single function and attempts to perform it well


## Compatibility
All scripts require Python version >= 3.5. All scripts are tested on Ubuntu 16.04/18.04 but should work on 
all recent Debian-based distributions, and maybe also on other Linux flavours.


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

# Example of a command line to run backup

# Included scripts

## lvm_snaphot.py
This script can create and remove the LVM snapshot. 
<!-- TODO: --> Write description


###  What this script does

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

### Typical usage

## manage_backups.py
### Typical usage

```
# Generate a name and an absolute path to backup file
BACKUP_FILE=manage_backups.py generate-name --backup-dest-dir /media/backups --prefix system_dump --extension tar.gz
# TODO: check exit code 

```



```
$TMP_DIR/lvm_snaphot.py --source-lvm-vg dmi-desktop --source-lvm-lv system --lvm-snapshot-name snap1 --mountpoint  /media/system_snapshot --lvm-snapshot-tmp-file /media/raw/1.tmp --loop-device /dev/loop5  snapshot-mount && \
#############
sleep 30 && \
#############
$TMP_DIR/lvm_snaphot.py --source-lvm-vg dmi-desktop --source-lvm-lv system --lvm-snapshot-name snap1 --mountpoint  /media/system_snapshot --remove-mountpoint --lvm-snapshot-tmp-file /media/raw/1.tmp --loop-device /dev/loop5 snapshot-unmount"
```