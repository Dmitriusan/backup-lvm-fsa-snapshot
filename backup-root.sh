#!/usr/bin/env bash

export SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# Parse script args ( thanks http://stackoverflow.com/questions/192249/how-do-i-parse-command-line-arguments-in-bash )
while [[ $# -ge 1 ]]; do
  key="$1"

  case $key in
      -v|--verbose)
      set -x
      shift
    ;;
      -h|--help)
      echo "-v|--verbose"
      exit 1
      shift
    ;;
    *)
      # unknown option
    ;;
  esac
  shift
done

# Load settings
SETTINGS_FILE=${SCRIPT_DIR}/../../settings
[ ! -f ${SETTINGS_FILE} ] && echo "Settings file $SETTINGS_FILE is not available" && exit 1
source ${SETTINGS_FILE}

[ -z "$SIGR_BACKUPS_AUTO_CREATED_LOCATION" ] && echo "$SIGR_BACKUPS_AUTO_CREATED_LOCATION not defined" && exit 1
[ -z "$SIGR_BACKUPS_LVM_TMP_SNAP_LOCATION" ] && echo "$SIGR_BACKUPS_LVM_TMP_SNAP_LOCATION not defined" && exit 1
[ -z "$SIGR_LVM_ROOT_FS_VG" ] && echo "$SIGR_LVM_ROOT_FS_VG not defined" && exit 1
[ -z "$SIGR_LVM_ROOT_FS_LV" ] && echo "$SIGR_LVM_ROOT_FS_LV not defined" && exit 1
[ -z "$CPU_COUNT" ] && echo "$CPU_COUNT not defined" && exit 1
[ -z "$SIGR_BACKUPS_ROOTFS_DAILY_LIMIT" ] && echo "$SIGR_BACKUPS_ROOTFS_DAILY_LIMIT not defined" && exit 1
[ -z "$SIGR_BACKUPS_ROOTFS_WEEKLY_LIMIT" ] && echo "$SIGR_BACKUPS_ROOTFS_WEEKLY_LIMIT not defined" && exit 1

# Detect day of week (1..7); 1 is Monday
DOW=$(date +%u)

# Generate filename
TIMESTAMP=`date +%F_%H-%M-%S`
WEEKLY_PREFIX=rootfs-dump-weekly
DAILY_PREFIX=rootfs-dump-daily
if [ "$DOW" -eq "7" ]; then
  BACKUP_NAME=${WEEKLY_PREFIX}-${TIMESTAMP}.fsa
else
  BACKUP_NAME=${DAILY_PREFIX}-${TIMESTAMP}.fsa
fi

SNAP_NAME=root_snapshot
BACKUP_DIR=${SIGR_BACKUPS_AUTO_CREATED_LOCATION}/rootfs-dumps
if [ ! -d ${BACKUP_DIR} ]; then
  mkdir -p ${BACKUP_DIR}
fi

# Check for previous unfinished backup
OLD_LOOP_DEV=$(losetup -a | grep ${SIGR_BACKUPS_LVM_TMP_SNAP_LOCATION} | cut -d : -f 1)

if [[ ! -z ${OLD_LOOP_DEV} ]]; then
  echo "Looks like previous backup was not properly finished, exiting"
  exit 1
fi

# Create tmp file for snapshot
TMP_LVM_SNAPSHOT_FILE=${SIGR_BACKUPS_LVM_TMP_SNAP_LOCATION}/tmp_lvm_snapshot.img
fallocate -l 16G ${TMP_LVM_SNAPSHOT_FILE}
RC=$?;
if [[ ${RC} != 0 ]]; then
  echo "Can not create tmp file for LVM snapshot"
  exit ${RC};
fi

# Create loopback device first
LOOPBACK_DEV=`losetup -f --show ${TMP_LVM_SNAPSHOT_FILE}`

pvcreate ${LOOPBACK_DEV}
vgextend ${SIGR_LVM_ROOT_FS_VG} ${LOOPBACK_DEV}
lvcreate -s -n ${SNAP_NAME} -L 15g ${SIGR_LVM_ROOT_FS_VG}/${SIGR_LVM_ROOT_FS_LV}

fsarchiver savefs -j${CPU_COUNT} -z8 -o ${BACKUP_DIR}/${BACKUP_NAME} /dev/${SIGR_LVM_ROOT_FS_VG}/${SNAP_NAME}
RC=$?;
if [[ ${RC} != 0 ]]; then
  echo "Backup failed, removing incomplete file"
  rm -f ${BACKUP_DIR}/${BACKUP_NAME}
fi

# Drop snapshot and remove physical volume
lvremove --force /dev/${SIGR_LVM_ROOT_FS_VG}/${SNAP_NAME}
vgreduce ${SIGR_LVM_ROOT_FS_VG} ${LOOPBACK_DEV}
pvremove ${LOOPBACK_DEV}
losetup -d ${LOOPBACK_DEV}
rm ${TMP_LVM_SNAPSHOT_FILE}

# Cleanup old backups (if current backup has been successfull)
if [[ ${RC} == 0 ]]; then
  # clean up daily archives
  DAILY_COUNT=`find ${BACKUP_DIR} -name "${DAILY_PREFIX}*" | sort | wc -l`
  let remove=$DAILY_COUNT-$SIGR_BACKUPS_ROOTFS_DAILY_LIMIT
  if [ ${remove} -gt 0 ]; then
    find ${BACKUP_DIR} -name "${DAILY_PREFIX}*" | sort | head -n ${remove} | xargs rm -f
  fi
  # clean up weekly archives
  WEEKLY_COUNT=`find ${BACKUP_DIR} -name "${WEEKLY_PREFIX}*" | sort | wc -l`
  let remove=$WEEKLY_COUNT-$SIGR_BACKUPS_ROOTFS_WEEKLY_LIMIT
  if [ ${remove} -gt 0 ]; then
    find ${BACKUP_DIR} -name "${WEEKLY_PREFIX}*" | sort | head -n ${remove} | xargs rm -f
  fi
fi

# Return proper exit code
exit ${RC}
