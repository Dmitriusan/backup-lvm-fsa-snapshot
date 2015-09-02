# backup-lvm-fsa-snapshot
Create snapshot of LVM volume and back it up using filesystem archiver. 
Snapshot volume is temporarily allocated on partition with backups.
Old snapshots are removed (max counts of daily and weekly dumps are 
configurable). Script is intended to be executed once every day.  


## Beware!
1. **Never** point backup file destination (--backup-dest-dir) to the same partition that is being 
backed up. **Snapshot space will be overfilled.**
1. **Never** point tmp snaphot file destination (--lvm-snapshot-tmp-file-dir) to the same partition that is being 
backed up. **Entire filesystem will hang!!!**
1. Never reboot computer without removing snapshot volume. On next boot,
temporary loop device will not be available, so operating system will fail
to boot.
1. If you did not follow advice 2. and rebooted while performing backup, 
you can fix everything by booting from live cd and running 
```
vgreduce --removemissing --force <your vg name>
```

## What script does
- Script installs fsarchiver package if it is not installed
- Script creates destination directory at --backup-dest-dir for storing backups 
if it does not exist 
- Script creates 15 GB tmp file in directory, specified via --lvm-snapshot-tmp-file-dir . 
If arg --tmp-dir-is-local is specified,
 file is created using fallocate call (fast, but applicable only to local filesystem). 
 Otherwise, if --tmp-dir-is-remote parameter is passed, temporary file is created 
 using dd.
- Then script creates a loop device on tmp file allocated earlier
- Then script creates an LVM physical volume for volume group specified via --source-lvm-volume-group.
 Physical volume is created on the loop device created beforehand.
- Then script creates an LVM snapshot for LVM logical volume specified via 
 --source-lvm-volume-group and --source-lvm-logical-volume options
- Then script creates a dump of snapshot volume. Backup is created via fsarchiver. 
Backup is compressed, compression uses all available CPUs, compression levels 
(see http://www.fsarchiver.org/Compression) are defined using --compression-level
 parameter.
- every Sunday, a weekly dump is created. On other days a daily dump is created.
 Limits of weekly and daily dump files are managed separately and 
 are defined using --daily-backup-max-count and
 --weekly-backup-max-count properties. Oldest dump files that exceed this limit are deleted.
 E.g. 7 dayly backups and 4 weekly backups mean that one has daily backups for the last week
 and weekly backups for the last month. 
- After backup is finished, script removes physical volume, loop device and tmp file created earlier.
- Then script removes old dumps (exceeding limits specified via --daily-backup-max-count 
 and --weekly-backup-max-count

## Example of command line to run backup
```
--compression-level 5
```