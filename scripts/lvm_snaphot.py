#!/usr/bin/env python3

import argparse
import math
import os
import pathlib
import subprocess

TIMEOUT = 60
INCREASED_TIMEOUT = TIMEOUT * 15

SNAPSHOT_MOUNT_ACTION = 'snapshot-mount'
SNAPSHOT_UNMOUNT_ACTION = 'snapshot-unmount'

DD_BLOCK_SIZE = 16


def configure_parser():
    parser = argparse.ArgumentParser(
        description='This script can create/remove the snapshot of an LVM volume and mount/unmount it.',
        epilog='Use at your own risk'
    )
    parser.add_argument('-v', '--verbose', action="count",
                        help="controls verbosity. May be specified multiple times")

    lvm_group = parser.add_argument_group("LVM snapshot", "Options related to LVM and LVM snapshot")
    lvm_group.add_argument("--lvm-volume-size-mb", type=int, default=4096,
                           help="Size of LVM snapshot volume in megabytes (default is 4096). This space is used "
                                "only for storing changes that are written to the source volume while snapshot exists. "
                                "If this space is exhausted, snapshot disappears.")
    lvm_group.add_argument("--source-lvm-vg", type=str, required=True,
                           help="Name of LVM volume group")
    lvm_group.add_argument("--source-lvm-lv", type=str, required=True,
                           help="Name of LVM logical volume")
    lvm_group.add_argument("--lvm-snapshot-name", type=str, required=True,
                           help="Name of LVM snapshot")
    lvm_group.add_argument("--lvm-snapshot-tmp-file", type=str,
                           help="Use if LVM volume has not enough unallocated space to create snapshot of a requested "
                                "size. A temporary file will be created at this path, and it will be mounted "
                                "as a loop device. This loop device will then be added as a physical volume into "
                                "a source volume group. When unmounting (or after unsuccessful mount), "
                                "the physical volume, loop device and temporary file will be attempted to be removed. "
                                "This option should be specified during unmount as well. Option should be always used "
                                "in conjunction with --loop-device option. Consider also --use-fallocate flag."
                                "WARNING: Never specify path that is located on a logical volume being snapshoted,"
                                "otherwise the filesystem will hang when snapshot is created")
    lvm_group.add_argument("--loop-device", type=str,
                           help="Full path to loop device. Valid only if --lvm-snapshot-tmp-file option is specified. "
                                "Loop device should already exist")
    lvm_group.add_argument("--use-fallocate", action="store_true",
                           help="Matters only when --lvm-snapshot-tmp-dir option is used. If specified, uses "
                                "'fallocate' method to create a temporary file. That is faster then dd command that is "
                                "used by default, but works only on some filesystems (e.g. local ext4). "
                                "Valid only for %s action" % SNAPSHOT_MOUNT_ACTION)

    backup_group = parser.add_argument_group("Mounting and unmounting", "Options related to mount stage")
    backup_group.add_argument("--mountpoint", type=str, required=True,
                              help="Target directory for snapshot mount. If it does not exist, it will be created.")
    backup_group.add_argument("--remove-mountpoint", action="store_true",
                              help="Remove snapshot mount directory during unmount. "
                                   "Valid only for %s action" % SNAPSHOT_UNMOUNT_ACTION)

    parser.add_argument('action', metavar="ACTION",
                        choices=[SNAPSHOT_MOUNT_ACTION, SNAPSHOT_UNMOUNT_ACTION],
                        help="%s creates snapshot and mounts it, %s unmounts snapshot and "
                             "removes it" % (SNAPSHOT_MOUNT_ACTION, SNAPSHOT_UNMOUNT_ACTION))
    return parser


def validate_args(args):
    if args.lvm_snapshot_tmp_file and not args.loop_device \
            or not args.lvm_snapshot_tmp_file and args.loop_device:
        raise ValueError("--lvm-snapshot-tmp-file option and --loop-device option should always be used together")

    if args.lvm_snapshot_tmp_file and not os.path.isabs(args.lvm_snapshot_tmp_file):
        raise ValueError("Argument passed to --lvm-snapshot-tmp-file option should be an absolute path")

    if args.loop_device and not os.path.isabs(args.loop_device):
        raise ValueError("Argument passed to --loop-device option should be an absolute path")

    if args.lvm_snapshot_tmp_file and not os.path.isabs(args.mountpoint):
        raise ValueError("Argument passed to --mountpoint option should be an absolute path")

    if args.action == SNAPSHOT_MOUNT_ACTION:
        # Quick validation
        if args.remove_mountpoint:
            raise ValueError("--remove-mountpoint flag is not applicable during mount")
    elif args.action == SNAPSHOT_UNMOUNT_ACTION:
        # Quick validation
        if args.use_fallocate:
            raise ValueError("--use-fallocate flag is not applicable during unmount")
    else:
        raise ValueError("Unknown action %s" % args.action)


def mount_snapshot(args):
    print("Performing %s action" % SNAPSHOT_MOUNT_ACTION)
    snapshot_dev = lvm_mapper_dev_name(args.source_lvm_vg, args.lvm_snapshot_name)
    source_lv_dev = lvm_mapper_dev_name(args.source_lvm_vg, args.source_lvm_lv)

    if os.path.exists(snapshot_dev):
        raise EnvironmentError("Device at %s already exists" % snapshot_dev)

    if not os.path.exists(source_lv_dev):
        raise EnvironmentError("Source logical volume device %s does not exist" % source_lv_dev)

    if args.lvm_snapshot_tmp_file:
        allocate_tmp_file(args)
        create_pv_based_on_tmp_file(args)

    create_snapshot(args)
    mountpoint = os.path.abspath(args.mountpoint)
    mount(snapshot_dev, mountpoint)


def allocate_tmp_file(args):
    dev_mapper_src_lv = lvm_mapper_dev_name(args.source_lvm_vg, args.source_lvm_lv)
    tmp_file = args.lvm_snapshot_tmp_file
    dir_containing_tmp_file = os.path.dirname(tmp_file)
    size = args.lvm_volume_size_mb + 16  # At least 1 more 4mb extent is required for LVM physical volume metadata
    use_fallocate = args.use_fallocate

    # Perform checks first
    if os.path.exists(tmp_file):
        raise EnvironmentError("tmp file %s already exists" % tmp_file)

    mounts = list_mounts()
    fs_containing_tmp_file = find_mount_point(dir_containing_tmp_file)
    if fs_containing_tmp_file in mounts and mounts[fs_containing_tmp_file] == dev_mapper_src_lv:
        raise EnvironmentError("Looks like you are trying to allocate tmp file on a logical volume that is being "
                               "snapshoted. That would lead to system freeze")

    statvfs_for_dir = os.statvfs(dir_containing_tmp_file)
    free_space = statvfs_for_dir.f_bavail * statvfs_for_dir.f_bsize / 1024 / 1024
    if size / free_space > 0.9:
        raise EnvironmentError(
            "Tmp file {0} of size {1:.0f} mb will take more then 90% of available space ({2:.0f} mb) "
            "at directory {2}. Refusing to allocate tmp file".format(tmp_file, free_space, dir_containing_tmp_file))

    print("Trying to allocate tmp file at {0} of size {1:.0f} mb. Free space "
          "available: {2:.0f} mb. Watchdog timer: will cancel operation if takes more then {3} seconds"
          .format(tmp_file, size, free_space, INCREASED_TIMEOUT))
    if use_fallocate:
        print("Using fallocate to create a temporary file")
        fallocate_cmd = ['/usr/bin/fallocate', '-l', "%sM" % size, tmp_file]
        subprocess.run(fallocate_cmd, timeout=INCREASED_TIMEOUT, check=True)
    else:
        print("Using dd with %s mb block size to create a temporary file" % DD_BLOCK_SIZE)
        dd_blocks = math.ceil(size / DD_BLOCK_SIZE)
        dd_cmd = ['/bin/dd', "if=/dev/zero", "of=%s" % tmp_file,
                  "bs=%sM" % DD_BLOCK_SIZE, "count=%s" % dd_blocks]
        subprocess.run(dd_cmd, timeout=INCREASED_TIMEOUT, check=True)


def create_pv_based_on_tmp_file(args):
    tmp_file = args.lvm_snapshot_tmp_file
    loop_device = args.loop_device

    if not pathlib.Path(loop_device).is_block_device():
        raise EnvironmentError("There is no block device at path %s. "
                               "Please check that it is an absolute path to device" % loop_device)

    print("Attaching tmp file to loop device %s" % loop_device)
    loop_dev_setup = ['/sbin/losetup', loop_device, tmp_file]
    subprocess.run(loop_dev_setup, timeout=TIMEOUT, check=True)

    print("Creating lvm physical volume on a loop device %s" % loop_device)
    pvcreate_cmd = ['/sbin/pvcreate', loop_device]
    subprocess.run(pvcreate_cmd, timeout=TIMEOUT, check=True)

    print("Adding this physical volume to volume group %s" % args.source_lvm_vg)
    vgextend_cmd = ['/sbin/vgextend', args.source_lvm_vg, loop_device]
    subprocess.run(vgextend_cmd, timeout=TIMEOUT, check=True)


def create_snapshot(args):
    source_volume_id = "%s/%s" % (args.source_lvm_vg, args.source_lvm_lv)
    print("Creating snapshot %s" % source_volume_id)
    snapshot_creation_cmd = ['/sbin/lvcreate', '-s', '-n', args.lvm_snapshot_name,
                             "-L", "%sm" % args.lvm_volume_size_mb, source_volume_id]
    subprocess.run(snapshot_creation_cmd, timeout=TIMEOUT, check=True)


def mount(snapshot_dev, mountpoint):
    if not os.path.isdir(mountpoint):
        if not os.path.exists(mountpoint):
            print("Creating mountpoint dir %s" % mountpoint)
            os.mkdir(mountpoint)
        else:
            raise ValueError("Expected mountpoint %s to be a directory" % mountpoint)

    if os.path.ismount(mountpoint):
        raise ValueError("Mountpoint %s seems to be already mounted" % mountpoint)

    print("Trying to detect filesystem on a snapshot volume...")
    blkid_cmd = ['/sbin/blkid', snapshot_dev]
    blkid_result = subprocess.run(blkid_cmd, stdout=subprocess.PIPE, timeout=TIMEOUT,
                                  check=True, universal_newlines=True)
    # Example of blkid output:
    # /dev/vg1/system: UUID="1492fdc0-e025-1111-9f27-23f422f33551" TYPE="ext4"
    blkid_info = str(blkid_result.stdout).split()
    fs_type = next((s.split('"')[1] for s in blkid_info if s.startswith('TYPE="')))
    print("Detected snapshot filesystem type is %s" % fs_type)
    mount_options = ["ro"]
    if fs_type in ["ext3", "ext4"]:
        # Don't try to check filesystem or attempt to replay journal. Required because snapshot fs is dirty
        # https://digital-forensics.sans.org/blog/2011/06/14/digital-forensics-mounting-dirty-ext4-filesystems
        mount_options.append("noload")

    print("Mounting snapshot device %s to mountpoint %s" % (snapshot_dev, mountpoint))
    mount_cmd = ['/bin/mount', "-o", ",".join(mount_options), snapshot_dev, mountpoint]
    subprocess.run(mount_cmd, timeout=TIMEOUT, check=True)


def unmount_snapshot(args):
    print("Performing %s action" % SNAPSHOT_UNMOUNT_ACTION)
    snapshot_dev = lvm_mapper_dev_name(args.source_lvm_vg, args.lvm_snapshot_name)
    mountpoint = os.path.abspath(args.mountpoint)
    unmount(args.source_lvm_vg, args.lvm_snapshot_name, mountpoint, args)

    remove_snapshot_lv(args, snapshot_dev)

    if args.lvm_snapshot_tmp_file:
        remove_pv_based_on_tmp_file(args)
        remove_tmp_file(args)


def remove_snapshot_lv(args, snapshot_dev):
    snapshot_volume_id = "%s/%s" % (args.source_lvm_vg, args.lvm_snapshot_name)
    if os.path.exists(snapshot_dev):
        print("Removing snapshot volume %s" % snapshot_volume_id)
        snapshot_removal_cmd = ['/sbin/lvremove', '--force', snapshot_volume_id]
        subprocess.run(snapshot_removal_cmd, timeout=TIMEOUT, check=True)
    else:
        print("Looks like snapshot volume %s does not exist" % snapshot_volume_id)


def unmount(vg_name, snapshot_name, mountpoint, args):
    if os.path.exists(mountpoint):
        dev_mapper_snapshot = lvm_mapper_dev_name(vg_name, snapshot_name)
        # check if partition is mounted

        mounts = list_mounts()
        if mountpoint in mounts and mounts[mountpoint] == dev_mapper_snapshot:
            print("Unmounting snapshot dev {0} from mountpoint {1}".format(dev_mapper_snapshot, mountpoint))
            unmount_cmd = ['/bin/umount', dev_mapper_snapshot]
            subprocess.run(unmount_cmd, timeout=TIMEOUT, check=True)
        else:
            print("Looks like device {0} is not mounted to {1}, skipping unmount"
                  .format(dev_mapper_snapshot, mountpoint))

        if os.path.isdir(mountpoint):
            if args.remove_mountpoint:
                print("Removing mountpoint %s" % mountpoint)
                os.rmdir(mountpoint)
        else:
            raise "Mountpoint %s is expected to be a directory" % mountpoint
    else:
        print("Looks like mountpoint %s does not exist" % mountpoint)


def remove_pv_based_on_tmp_file(args):
    pvs = list_pvs()
    loop_device = args.loop_device
    vg_name = args.source_lvm_vg
    tmp_file = args.lvm_snapshot_tmp_file

    if loop_device in pvs and pvs[loop_device] == vg_name:
        print("Removing physical volume {0} from volume group {1}".format(loop_device, vg_name))
        vgreduce_cmd = ['/sbin/vgreduce', vg_name, loop_device]
        subprocess.run(vgreduce_cmd, timeout=TIMEOUT, check=True)

    if loop_device in pvs and pvs[loop_device] == loop_device:  # when pv is not in vg, it displays as its path
        print("Destroying physical volume {0}".format(loop_device))
        pvremove_cmd = ['/sbin/pvremove', loop_device]
        subprocess.run(pvremove_cmd, timeout=TIMEOUT, check=True)

    loop_devices = list_loop_devices()
    if loop_device in loop_devices:
        if loop_devices[loop_device] == tmp_file:
            print("Detaching loop device {0}".format(loop_device))
            lo_detach_cmd = ['/sbin/losetup', '-d', loop_device]
            subprocess.run(lo_detach_cmd, timeout=TIMEOUT, check=True)
        else:
            print("Looks like something other then tmp file {0} is attached to loop device {1}. Not detaching "
                  "file {2} from loop device {1}.".format(tmp_file, loop_device, loop_devices[loop_device]))


def remove_tmp_file(args):
    tmp_file = args.lvm_snapshot_tmp_file
    if os.path.exists(tmp_file):
        if os.path.isfile(tmp_file):
            print("Removing tmp file %s" % tmp_file)
            os.remove(tmp_file)
        else:
            print("File at path %s is not a regular file, not removing it" % tmp_file)


# region Utils

def list_mounts():
    """
    Lists system mounts
    :return: dictionary {mountpoint -> device}
    """
    cmd_result = subprocess.run(['/bin/findmnt', '-P'], stdout=subprocess.PIPE, timeout=TIMEOUT,
                                universal_newlines=True)
    # Example of mount output:
    # TARGET="/" SOURCE="/dev/sda1" FSTYPE="ext4" OPTIONS="rw,noatime,errors=remount-ro,data=ordered"
    result = {}
    for line in cmd_result.stdout.splitlines():
        if not line:
            continue
        target = None
        source = None
        for kv in line.split():
            if kv.startswith("TARGET="):
                target = kv.split('"')[1]
            elif kv.startswith("SOURCE="):
                source = kv.split('"')[1]
        if target and source:
            result[target] = source
        else:
            raise EnvironmentError("Could not parse findmnt output %s " % line)
    return result


def find_mount_point(path):
    """
    Finds the nearest directory in path that is a mountpoint
    Source: https://stackoverflow.com/a/38326779
    :param path: path to some file/directory
    :return: path to mountpoint
    """
    if not os.path.islink(path):
        path = os.path.abspath(path)
    elif os.path.islink(path) and os.path.lexists(os.readlink(path)):
        path = os.path.realpath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
        if os.path.islink(path) and os.path.lexists(os.readlink(path)):
            path = os.path.realpath(path)
    return path


def lvm_mapper_dev_name(vg_name, lv_name):
    """
    Returns path to lvm lv device as /dev/mapper/my--vg-my--lv.
    This device path is represented at mount command output
    :param vg_name:
    :param lv_name:
    :return:
    """
    return "/dev/mapper/{0}-{1}".format(lvm_name_escaped(vg_name), lvm_name_escaped(lv_name))


def lvm_name_escaped(s):
    """
    Dashes in LVM volume names and group names are replaced by double dashes in names of entries at /dev/mapper/.
    :param s: volume name or group name
    :return: escaped string
    """
    return s.replace("-", "--")


def list_pvs():
    """
    Lists LVM physical volumes
    :return: dictionary {physical volume -> volume group}
    """
    cmd_result = subprocess.run(['/sbin/pvs', '-o', 'pv_name,vg_name', '--noheadings',
                                 '--separator', ';'], stdout=subprocess.PIPE, timeout=TIMEOUT,
                                universal_newlines=True)
    # Example of output:
    #     /dev/loop5;main-vg
    result = {}
    for line in cmd_result.stdout.splitlines():
        if line.strip():
            parts = line.split(";")
            pv_name = parts[0].strip()
            vg_name = parts[1].strip()
            result[pv_name] = vg_name
    return result


def list_loop_devices():
    """
    Lists active loop devices
    :return: dictionary {loop device -> file}
    """
    cmd_result = subprocess.run(['/sbin/losetup', '-a'], stdout=subprocess.PIPE, timeout=TIMEOUT,
                                universal_newlines=True)
    # Example of output:
    # /dev/loop5: [0052]:8651046 (/media/raw/1.tmp)
    result = {}
    for line in cmd_result.stdout.splitlines():
        if line.strip():
            parts = line.split()
            loop_device_name = parts[0].strip()[0:-1]
            attached_file = parts[2].strip()[1:-1]
            result[loop_device_name] = attached_file
    return result

# endregion


def main():
    parser = configure_parser()
    args, unknown_args = parser.parse_known_args()
    validate_args(args)

    if os.geteuid() != 0:
        raise EnvironmentError("This script requires root permissions, effective user id=%s" % os.geteuid())

    if args.action == SNAPSHOT_MOUNT_ACTION:
        # Quick validation
        if args.remove_mountpoint:
            raise ValueError("--remove-mountpoint flag is not applicable during mount")
        try:
            mount_snapshot(args)
        except Exception as e:
            print("Mounting snapshot failed, trying to clean things up")
            unmount_snapshot(args)
            raise e
    elif args.action == SNAPSHOT_UNMOUNT_ACTION:
        # Quick validation
        if args.use_fallocate:
            raise ValueError("--use-fallocate flag is not applicable during unmount")
        unmount_snapshot(args)


if __name__ == "__main__":
    main()
