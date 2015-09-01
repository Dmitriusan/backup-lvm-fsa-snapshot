# backup-lvm-fsa-snapshot
create snapshot of LVM volume and back it up using filesystem archiver. 
Snapshot volume is temporarily allocated on partition with backups.


## Beware!
1. Never point backup file destination to the same partition that is being 
backed up. Snapshot space will be overfilled.
2. Never reboot computer without removing snapshot volume. On next boot,
temporary loop device will not be available, so operating system will fail
to boot.
3. If you did not follow advice 2. and rebooted while performing backup, 
you can fix everything by booting from live cd and running 
```
vgreduce --removemissing --force <your vg name>
```