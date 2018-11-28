import argparse
import multiprocessing


FSARCHIVER="fsarchiver"
TGZ="tgz"


def configure_parser():
    parser = argparse.ArgumentParser(
        description='This script creates snapshot of LVM volume and backs it up to a given location.',
        epilog='Use at your own risk'
    )
    # parser.add_argument('target_host', type=str, help="target host that exposes ports")
    # parser.add_argument('target_host', type=str, help="target host that exposes ports")
    # ports_group = parser.add_argument_group("Port scope", "Selects which ports to forward")
    # ports_group.add_argument('--env', action="store_true", help="forward env ports")
    parser.add_argument('-v', '--verbose', action="count",
                        help="controls verbosity. May be specified multiple times")

    lvm_group = parser.add_argument_group("LVM and snapshot", "Options related to LVM and LVM snapshot")
    lvm_group.add_argument("--lvm-volume-size-mb", type=int, default=4096,
                           help="Size of LVM snapshot volume in megabytes (default is 4096). This space is used "
                                "only for storing changes that are written to the source volume while snapshot exists. "
                                "If this space is exhausted, snapshot disappears")
    lvm_group.add_argument("--source-lvm-volume-group", type=str, required=True,
                           help="Name of LVM volume group")
    lvm_group.add_argument("--source-lvm-logical-volume", type=str, required=True,
                           help="Name of LVM logical volume")
    lvm_group.add_argument("--lvm-snapshot-tmp-dir", type=str,
                           help="Use if LVM volume has no enough unallocated space to create snapshot of a requested "
                                "size. There will be created a temporary file at this dir, and it will be mounted "
                                "as a loop device. This loop device will then be added as a physical device into "
                                "a source volume group. At the end of the backup process (either successful or not), "
                                " the physical volume, loop device and temporary file will be removed.")
    lvm_group.add_argument("--use-fallocate", action="store_true",
                           help="Matters only if --lvm-snapshot-tmp-dir option is used. If specified, uses fallocate "
                                "to create a temporary file. That is faster then dd, but works "
                                "only on local filesystem (e.g. ext4)")

    backup_group = parser.add_argument_group("Backups", "Options related to backups")
    backup_group.add_argument("--backup-dest-dir", type=str, required=True,
                              help="Target directory for storing backups")
    backup_group.add_argument("--backup-method", choices=[FSARCHIVER, TGZ], required=True,
                              help='Backup method to use. fsarchiver method uses "fsarchiver" program, tgz stands '
                                   'for gzipped tar')
    backup_group.add_argument("--compression-level", type=int, required=True,
                              help="Number from 1 to 9. Compression level, 1 stands stands for fastest, "
                                   "9 stands for best compression")
    backup_group.add_argument("--daily-backup-max-count", type=int, default=5,
                              help="How many daily backups should be stored at location specified by "
                                   "--backup-dest-dir . Older backups are removed. The default value is 5.")
    backup_group.add_argument("--weekly-backup-max-count", type=int, default=2,
                              help="How many weekly backups should be stored at location specified by "
                                   "--backup-dest-dir . Older backups are removed. The default value is 2.")

    return parser


def install_required_packages(args):
    if args.backup_method == FSARCHIVER:
        # TODO: check if fsarchiver is installed
        # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
        pass
    elif args.backup_method == TGZ:
        # TODO: check if pigz is installed
        pass
    # TODO: if any package is not installed, run apt-get update
    #apt-get -y update
    #apt-get -y install fsarchiver

    pass


def main():
    parser = configure_parser()
    args = parser.parse_args()
    install_required_packages(args)
    # TODO : continue


if __name__ == "__main__":
    main()
