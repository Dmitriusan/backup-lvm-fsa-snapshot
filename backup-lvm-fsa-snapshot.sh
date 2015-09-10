#!/usr/bin/env bash

export SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

SNAPSHOT_VOLUME_SIZE=15360

# Parse script args ( thanks http://stackoverflow.com/questions/192249/how-do-i-parse-command-line-arguments-in-bash )
while [[ $# -ge 1 ]]; do
  key="$1"

  case ${key} in
    -v|--verbose)
      set -x
    ;;

    --backup-dest-dir)
      BACKUPS_AUTO_CREATED_LOCATION="$2"
      shift
    ;;

    --source-lvm-volume-group)
      LVM_ROOT_FS_VG="$2"
      shift
    ;;

    --source-lvm-logical-volume)
      LVM_ROOT_FS_LV="$2"
      shift
    ;;

    --lvm-snapshot-tmp-file-dir)
      LVM_SNAP_TMP_FILE_DIR="$2"
      shift
    ;;

    --tmp-dir-is-local)     # Use fallocate to create tmp file
      TMP_DIR_TYPE="local"
    ;;

    --tmp-dir-is-remote)    # On remote dir, fallocate is not available, use dd to create tmp file
      TMP_DIR_TYPE="remote"
    ;;

    --tmp-dir-is-lvm)    # Use when LVM volume group has enough spare space to create a tmp snapshot volume
      TMP_DIR_TYPE="lvm"
    ;;

    --snapshot-volume-size-mb) # Size of tmp snapshot volume (defaults to 15360 megabytes)
      SNAPSHOT_VOLUME_SIZE="$2"
      shift
    ;;

    --daily-backup-max-count)
      DAILY_BACKUP_MAX_COUNT="$2"
      shift
    ;;

    --weekly-backup-max-count)
      WEEKLY_BACKUP_MAX_COUNT="$2"
      shift
    ;;

    --compression-level)
      COMPRESSION_LEVEL="$2"
      shift
    ;;

    -h|--help)
      echo "Supported options:"
      echo "-v|--verbose"
      echo "-h|--help"
      echo "--backup-dest-dir <place to store backups>"
      echo "--source-lvm-volume-group <volume group name>"
      echo "--source-lvm-logical-volume <logical volume name>"
      echo "--lvm-snapshot-tmp-file-dir <place to store tmp file for snapshot writes>"
      echo "--tmp-dir-is-local | --tmp-dir-is-remote --tmp-dir-is-lvm"
      echo "--snapshot-volume-size-mb <number, megabytes>"
      echo "--daily-backup-max-count <number>"
      echo "--weekly-backup-max-count <number>"
      echo "--compression-level <number>"
      exit 1
    ;;

    *)
      # unknown option
      echo "Unknown option $key"
      exit 1
    ;;
  esac
  shift
done

CPU_COUNT=`grep -c ^bogomips /proc/cpuinfo`

# Check arguments
[ -z "$BACKUPS_AUTO_CREATED_LOCATION" ] && echo "--backup-dest-dir not specified" && exit 1
[ -z "$LVM_ROOT_FS_VG" ] && echo "--source-lvm-volume-group not specified" && exit 1
[ -z "$LVM_ROOT_FS_LV" ] && echo "--source-lvm-logical-volume not specified" && exit 1
[ -z "$LVM_SNAP_TMP_FILE_DIR" ] && echo "--lvm-snapshot-tmp-file-dir not specified" && exit 1
[ -z "$TMP_DIR_TYPE" ] && echo "Either --tmp-dir-is-local, --tmp-dir-is-remote or --tmp-dir-is-lvm should be specified" && exit 1
[ -z "$DAILY_BACKUP_MAX_COUNT" ] && echo "--daily-backup-max-count not specified" && exit 1
[ -z "$WEEKLY_BACKUP_MAX_COUNT" ] && echo "--weekly-backup-max-count not specified" && exit 1
[ -z "$COMPRESSION_LEVEL" ] && echo "--compression-level not specified" && exit 1

# install fsarchiver
apt-get -y update
apt-get -y install fsarchiver


# Detect day of week (1..7); 1 is Monday
DOW=$(date +%u)

# Generate filename
TIMESTAMP=`date +%F_%H-%M-%S`
DUMP_PREFIX=${LVM_ROOT_FS_VG}-${LVM_ROOT_FS_LV}
WEEKLY_PREFIX=${DUMP_PREFIX}-dump-weekly
DAILY_PREFIX=${DUMP_PREFIX}-dump-daily
if [ "$DOW" -eq "7" ]; then
  BACKUP_NAME=${WEEKLY_PREFIX}-${TIMESTAMP}.fsa
else
  BACKUP_NAME=${DAILY_PREFIX}-${TIMESTAMP}.fsa
fi

SNAP_NAME=${LVM_ROOT_FS_LV}_snapshot
BACKUP_DIR=${BACKUPS_AUTO_CREATED_LOCATION}/${DUMP_PREFIX}-dumps
if [ ! -d ${BACKUP_DIR} ]; then
  mkdir -p ${BACKUP_DIR}
fi

# Check for previous unfinished backup
OLD_LOOP_DEV=$(losetup -a | grep ${LVM_SNAP_TMP_FILE_DIR} | cut -d : -f 1)

if [[ ! -z ${OLD_LOOP_DEV} ]]; then
  echo "Looks like previous backup was not properly finished, exiting. Need manual intervention"
  exit 1
fi

# Create tmp file for snapshot
mkdir -p ${LVM_SNAP_TMP_FILE_DIR}
TMP_LVM_SNAPSHOT_FILE=${LVM_SNAP_TMP_FILE_DIR}/tmp_lvm_snapshot.img

if [ "${TMP_DIR_TYPE}" == "local" ]; then # Use fallocate - only local filesystem
  fallocate -l ${SNAPSHOT_VOLUME_SIZE}MB ${TMP_LVM_SNAPSHOT_FILE}
  RC=$?;
elif [ "${TMP_DIR_TYPE}" == "remote" ]; then # Use dd - universal method
  # Get ceiling integer by division for any snapshot size
  let count = "( $SNAPSHOT_VOLUME_SIZE + 16 - 1 ) / 16 "
  dd if=/dev/zero of=${TMP_LVM_SNAPSHOT_FILE} bs=16M count=${count}
  RC=$?;
fi

if [ "${TMP_DIR_TYPE}" != "lvm" ]; then
  if [[ ${RC} != 0 ]]; then
    echo "Can not create tmp file for LVM snapshot"
    exit ${RC};
  fi

  # Create loopback device first
  LOOPBACK_DEV=`losetup -f --show ${TMP_LVM_SNAPSHOT_FILE}`

  pvcreate ${LOOPBACK_DEV}
  vgextend ${LVM_ROOT_FS_VG} ${LOOPBACK_DEV}
fi  # Otherwise use spare space on LVM partition - do nothing

lvcreate -s -n ${SNAP_NAME} -L ${SNAPSHOT_VOLUME_SIZE}M ${LVM_ROOT_FS_VG}/${LVM_ROOT_FS_LV}

fsarchiver savefs -j${CPU_COUNT} -z${COMPRESSION_LEVEL} -o ${BACKUP_DIR}/${BACKUP_NAME} /dev/${LVM_ROOT_FS_VG}/${SNAP_NAME}
RC=$?;
if [[ ${RC} != 0 ]]; then
  echo "Backup failed, removing incomplete file"
  rm -f ${BACKUP_DIR}/${BACKUP_NAME}
fi

# Drop snapshot and remove physical volume
lvremove --force /dev/${LVM_ROOT_FS_VG}/${SNAP_NAME}

if [ "${TMP_DIR_TYPE}" != "lvm" ]; then
  vgreduce ${LVM_ROOT_FS_VG} ${LOOPBACK_DEV}
  pvremove ${LOOPBACK_DEV}
  losetup -d ${LOOPBACK_DEV}
  rm ${TMP_LVM_SNAPSHOT_FILE}
fi  # Otherwise use spare space on LVM partition - do nothing

# Cleanup old backups (if current backup has been successfull)
if [[ ${RC} == 0 ]]; then
  # clean up daily archives
  DAILY_COUNT=`find ${BACKUP_DIR} -name "${DAILY_PREFIX}*" | sort | wc -l`
  let remove=$DAILY_COUNT-$DAILY_BACKUP_MAX_COUNT
  if [ ${remove} -gt 0 ]; then
    find ${BACKUP_DIR} -name "${DAILY_PREFIX}*" | sort | head -n ${remove} | xargs rm -f
  fi
  # clean up weekly archives
  WEEKLY_COUNT=`find ${BACKUP_DIR} -name "${WEEKLY_PREFIX}*" | sort | wc -l`
  let remove=$WEEKLY_COUNT-$WEEKLY_BACKUP_MAX_COUNT
  if [ ${remove} -gt 0 ]; then
    find ${BACKUP_DIR} -name "${WEEKLY_PREFIX}*" | sort | head -n ${remove} | xargs rm -f
  fi
fi

# Return proper exit code
exit ${RC}
