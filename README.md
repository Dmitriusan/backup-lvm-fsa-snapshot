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
[lvm_snapshot.py](https://github.com/Dmitriusan/backup-lvm-fsa-snapshot/blob/master/docs/lvm_snapshot.py)

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