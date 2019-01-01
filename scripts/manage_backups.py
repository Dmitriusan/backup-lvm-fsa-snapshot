#!/usr/bin/env python3

import argparse
import os
import re
import sys
from datetime import datetime

GENERATE_NAME_ACTION = 'generate-name'
AUTO_CLEAN_ACTION = 'auto-clean'
REMOVE_UNSUCCESSFUL_ACTION = 'remove-unsuccessful'

DATE_STRING_FORMAT = '%Y%m%d_%H%M%S'


# region Argument parsing

def configure_parser():
  parser = argparse.ArgumentParser(
    description='This script is intended for managing auto-created regular backup files. It can generate a filename, '
                'and auto-clean old backup files according to configured limits.',
    epilog='Use at your own risk',
    formatter_class=argparse.RawTextHelpFormatter
  )
  parser.add_argument('--backup-dest-dir', type=str, required=True,
                      help="A destination directory where backups should be stored. Will be created recursively if "
                           "does not exist")
  parser.add_argument('-v', '--verbose', action="count",
                      help="controls verbosity. May be specified multiple times")
  parser.add_argument("--prefix", type=str, required=True,
                      help="String that should be prepended to a name of the backup file")
  parser.add_argument("--extension", type=str, required=True,
                      help="String that should be appended to a name of the backup file")

  auto_clean_group = parser.add_argument_group('Options for an "%s" action' % AUTO_CLEAN_ACTION,
                                               'Auto-clean old backup files')
  auto_clean_group.add_argument("--dry-mode", help="Don't perform any actions. Just show what would be done \n")
  auto_clean_group.add_argument("--daily-backups-max-count", type=int, default=5,
                                help="Max number of daily backups (performed during last 7 days) that can be \n"
                                     "stored at a location specified by the --backup-dest-dir parameter. \n"
                                     "The default value is 5. \n")
  auto_clean_group.add_argument("--weekly-backups-max-count", type=int, default=3,
                                help="Max number of weekly backups (performed during last 31 days) that can be \n"
                                     "stored at a location specified by the --backup-dest-dir parameter. \n"
                                     "The default value is 3. \n")
  auto_clean_group.add_argument("--monthly-backups-max-count", type=int, default=6,
                                help="Max number of monthly backups (performed during last 365 days) that can be \n"
                                     "stored at a location specified by the --backup-dest-dir parameter. \n"
                                     "The default value is 6. \n")
  auto_clean_group.add_argument("--yearly-backups-max-count", type=int, default=0,
                                help="Max number of yearly backups (performed over 365 days ago) that can be \n"
                                     "stored at a location specified by the --backup-dest-dir parameter. \n"
                                     "The default value is 0. \n")

  remove_unsuccessful_group = parser.add_argument_group('Options for a "%s" action' % REMOVE_UNSUCCESSFUL_ACTION,
                                                        'Remove leftovers after a previous unsuccessful backup')
  remove_unsuccessful_group.add_argument("--remove-file", type=str,
                                         help="Absolute path to a file that could be leftover after an \n"
                                              "unsuccessful backup (it will be removed if exists) \n")

  parser.add_argument('action', metavar="ACTION",
                      choices=[GENERATE_NAME_ACTION, AUTO_CLEAN_ACTION, REMOVE_UNSUCCESSFUL_ACTION],
                      help=(
                        'The "{0}" action generates an absolute filename for a backup file and \n'
                        'writes it to stdout. Filename includes date formatted as {1}\n'
                        'If the file already exists, action fails with -1 exit code and prints /dev/null as \n'
                        'a safeguard against breaking substitution logic at shell scripts. \n'
                        'If the destination directory does not exist, it will be created\n'
                        ' \n'
                        'The "{2}" action removes old backup files according to configured limits. \n'
                        'This action also tries to sparingly balance daily, weekly and monthly backups between \n'
                        'periods using a complicated rating formula to get the best coverage (the idea is \n'
                        'similar to RRD file format). This action uses the date from a filename, and not a '
                        'filesystem timestamp. \n \n'
                        ' \n'
                        'The "{3}" action removes a backup file that is a leftover from a previous \n'
                        'unsuccessful backup (if it exists). If the file does not exist, action just exits \n'
                        'with a zero exit code. If any other error occurs, the action exits with a non-zero \n'
                        'exit code \n'
                      ).format(GENERATE_NAME_ACTION, DATE_STRING_FORMAT, AUTO_CLEAN_ACTION, REMOVE_UNSUCCESSFUL_ACTION))
  return parser


def validate_args(args):
  if args.remove_file and not args.action == REMOVE_UNSUCCESSFUL_ACTION:
    raise ValueError("--remove-file option is only valid for action '%s'" % REMOVE_UNSUCCESSFUL_ACTION)
# endregion


# region Name generation
def generate_name(args):
  """

  :param args:
  :return: tuple (generated_name_string, exit_code)
  """
  now = datetime.now()
  timestamp = now.strftime(DATE_STRING_FORMAT)
  filename = "{0}__{1}{2}".format(args.prefix, timestamp, args.extension)
  full_path = os.path.abspath(os.path.join(args.backup_dest_dir, filename))

  error = None
  if os.path.exists(full_path):
    error = "File %s already exists\n" % full_path
  elif os.path.exists(args.backup_dest_dir) and not os.path.isdir(args.backup_dest_dir):
    error = "--backup-dest-dir argument points to an existing file %s that is not a directory\n" % args.backup_dest_dir

  if error:
    full_path = "/dev/null"  # a safeguard against breaking substitution logic at shell scripts
    sys.stderr.write(error)
    return full_path, 1

  if not os.path.exists(args.backup_dest_dir):
    os.makedirs(args.backup_dest_dir)

  return full_path, 0
# endregion


# region Auto clean
def auto_clean(args):
  if not os.path.isdir(args.backup_dest_dir):
    msg = "Path %s is not a directory" % args.backup_dest_dir
    return msg, 1

  backups = _list_backup_files(args)
  files_to_preserve = _choose_valuable_backups(backups, args)

  stdout = []
  backups_to_remove = [backup for backup in backups if backup not in files_to_preserve]
  for backup in backups_to_remove:
    if backup not in files_to_preserve:
      if args.dry_mode:
        stdout.append("Would remove old backup %s" % backup.filename)
      else:
        stdout.append("Removing old backup %s" % backup.filename)
        os.remove(backup.path)
  if not args.dry_mode:
    stdout.append("Removed %s old backup files." % len(backups_to_remove))
  return "\n".join(stdout), 0


def _choose_valuable_backups(backups, args):
  """
  :param backups: source list of backups (sorted ascending by timestamps, e.g. the most recent backup is last)
  :return: a list of backups that are valuable and should be preserved
  """
  result = []
  daily_bucket, weekly_bucket, monthly_bucket, yearly_bucket = _put_to_buckets_by_time_periods(backups)

  levels = [
    (daily_bucket, args.daily_backups_max_count),
    (weekly_bucket, args.weekly_backups_max_count),
    (monthly_bucket, args.monthly_backups_max_count),
    (yearly_bucket, args.yearly_backups_max_count)
  ]
  carry = 0   # Vacant slots for backups that are carried to a next level
  unused = []  # Backups that were not used on a previous level
  for bucket, limit in levels:
    for unused_backup in unused:
      unused_backup.rating = 0
      bucket.put_backup(unused_backup)
    promoted_backups, unused, carry = _promote_best_backups_from_bucket(bucket, limit + carry)
    result += promoted_backups

  return result


def _put_to_buckets_by_time_periods(backups):
  """
  Splits list of backups into separate buckets by time periods (last 7 days, last 31 day, last 365 days, other)
  :param backups: list of backups, sorted asc by timestamp
  :return: tuple of (daily_backups_bucket, weekly_backups_bucket, monthly_backups_bucket, yearly_backups_bucket),
   backups within each bucket are sorted asc by timestamp
  """

  day_seconds = 24 * 3600

  timestamp_now = datetime.now().timestamp()
  timestamp_7__days_ago = timestamp_now - 7 * day_seconds
  timestamp_31_days_ago = timestamp_now - 31 * day_seconds
  timestamp_365_days_ago = timestamp_now - 365 * day_seconds

  daily_backups = Bucket(timestamp_7__days_ago, timestamp_now)
  weekly_backups = Bucket(timestamp_31_days_ago, timestamp_7__days_ago)
  monthly_backups = Bucket(timestamp_365_days_ago, timestamp_31_days_ago)
  yearly_backups = Bucket(0, timestamp_365_days_ago)

  for backup in backups:
    if backup.timestamp >= timestamp_7__days_ago:
      daily_backups.put_backup(backup)
    elif timestamp_7__days_ago > backup.timestamp >= timestamp_31_days_ago:
      weekly_backups.put_backup(backup)
    elif timestamp_31_days_ago > backup.timestamp >= timestamp_365_days_ago:
      monthly_backups.put_backup(backup)
    elif timestamp_365_days_ago > backup.timestamp:
      yearly_backups.put_backup(backup)
  return daily_backups, weekly_backups, monthly_backups, yearly_backups


def _promote_best_backups_from_bucket(bucket, max_number_of_results):
  """
  :param bucket: a bucket with backups
  :param max_number_of_results: the maximal expected number of results
  :return: a tuple of (list of promoted backups, unused_backups, vacant_places), where vacant_places is
  a difference between expected number of resuls and the actual number of results.
  """
  # TODO: implement
  # TODO define proper condition
  while True:
    buckets = _calculate_rating() # TODO: make method return a value
    # TODO: merge buckets with previous results
  for bucket in buckets:
    apply_positional_rating_correction(bucket) # TODO: merge results with other results
  # TODO: select best results from list
  return [], [], 0  # TODO: return real results


def _calculate_rating(parent_bucket, total_rating):
  """
  :param parent_bucket:
  :param total_rating:
  :return: a list of backups
  """
  segments = 3  # Base number of segments on each interval

  draft_list_of_buckets = []
  step = (parent_bucket.period_end_timestamp - parent_bucket.period_start_timestamp) / 3
  start_timestamp = parent_bucket.period_start_timestamp
  # Compose a draft list of non-empty buckets (some buckets in this list may contain more than 1 backup)
  for i in range(0, segments):
    end_timestamp = start_timestamp + step
    current_bucket = Bucket(start_timestamp, end_timestamp)
    for backup in parent_bucket.get_backups():
      if start_timestamp <= backup.timestamp < end_timestamp:
        current_bucket.put_backup(backup)
    if len(current_bucket.get_backups()) > 0:
      draft_list_of_buckets.append(current_bucket)
    start_timestamp = end_timestamp

  # Calculate rating of each backup, and populate a list of results
  resulting_list_of_backups = []
  for bucket in draft_list_of_buckets:
    share_of_rating = total_rating / len(draft_list_of_buckets)
    if len(bucket.get_backups()) == 1:
      backup = bucket.get_backups()[0]
      backup.rating = share_of_rating
      resulting_list_of_backups.append(backup)
    else:
      resulting_list_of_backups += _calculate_rating(bucket, share_of_rating)

  return draft_list_of_buckets


def apply_positional_rating_correction(bucket):
  """
  Correct rating of each backup to ln(current_rating) relatively to period bounds. This tends to promote
  the most recent backups
  :param bucket:
  :return:
  """
  # TODO: implement
  pass

# endregion


# region Remove unsuccessful
def remove_unsuccessful(args):
  # Perform paranoic checks
  if not os.path.exists(args.remove_file):
    return "File %s does not exist." % args.remove_file, 0

  if not os.path.isfile(args.remove_file):
    return "Path %s points to a directory or some other non-regular " \
           "file." % args.remove_file, 1

  filename = os.path.basename(args.remove_file)
  if not filename.endswith(args.extension):
    msg = "File name %s does not end with extension '%s'. Probably you " \
          "specified a wrong file." % (filename, args.extension)
    return msg, 1
  elif not filename.startswith(args.prefix):
    msg = "File name %s does not start with prefix '%s'. Probably you " \
          "specified a wrong file." % (args.remove_file, args.prefix)
    return msg, 1

  target_dir = os.path.abspath(os.path.dirname(args.remove_file))
  backups_dir = os.path.abspath(args.backup_dest_dir)
  if target_dir != backups_dir:
    msg = "Target file is at directory %s, and backup destination dir is %s. Probably you " \
          "specified a wrong path." % (target_dir, backups_dir)
    return msg, 1
  # If all checks passed, remove the file
  os.remove(args.remove_file)
  return "Removed %s" % args.remove_file, 0
# endregion


# region Common code
class Backup:
  """
  A representation of backup file on disk. Contains additional metainfo computed at runtime
  """
  def __init__(self, path, filename, timestamp):
    self.path = path
    self.filename = filename
    self.timestamp = timestamp
    self.rating = 0

  def __repr__(self):
    return "{}({!r})".format(self.__class__.__name__, self.__dict__)

  def __eq__(self, other):
    if isinstance(other, Backup):
      return self.path == other.path and \
        self.filename == other.filename and \
        self.timestamp == other.timestamp and \
        self.rating == other.rating
    return NotImplemented


class Bucket:
  """
  A group of backups that relies to some time period.
  """
  def __init__(self, period_start_timestamp, period_end_timestamp, backups=None):
    if backups is None:
      self._backups = []
    else:
      self._backups = backups
    self.period_start_timestamp = period_start_timestamp
    self.period_end_timestamp = period_end_timestamp

  def __repr__(self):
    return "{}({!r})".format(self.__class__.__name__, self.__dict__)

  def __eq__(self, other):
    if isinstance(other, Bucket):
      return self._backups == other._backups and \
             self.period_start_timestamp == other.period_start_timestamp and \
             self.period_end_timestamp == other.period_end_timestamp
    return NotImplemented

  def put_backup(self, backup):
    self._backups.append(backup)

  def get_backups(self):
    return self._backups


def _list_backup_files(args):
  """
  Lists backup files at a directory.
  :param args: application args
  :return: a list of backups sorted ascending by timestamps, e.g. the most recent backup is last
  """
  result = []
  # Regex of expected filename
  regex_str = '^%s__(20\\d{6}_\\d{6})%s$' % (re.escape(args.prefix), re.escape(args.extension))
  regex = re.compile(regex_str)

  for filename in os.listdir(args.backup_dest_dir):
    full_path = os.path.join(os.path.abspath(args.backup_dest_dir), filename)
    if not os.path.isfile(full_path):
      continue
    match = re.search(regex, filename)
    if not match:
      continue
    date_str = match.group(1)
    file_time = datetime.strptime(date_str, DATE_STRING_FORMAT)
    backup = Backup(full_path, filename, file_time.timestamp())
    result.append(backup)
  return sorted(result, key=lambda item: item.timestamp)
# endregion


def main():
  parser = configure_parser()
  args, unknown_args = parser.parse_known_args()

  args.extension = args.extension if args.extension.startswith(".") else ".%s" % args.extension
  validate_args(args)

  exit_code = 0
  stdout = ''
  if args.action == GENERATE_NAME_ACTION:
    stdout, exit_code = generate_name(args)
  elif args.action == AUTO_CLEAN_ACTION:
    stdout, exit_code = auto_clean(args)
  elif args.action == REMOVE_UNSUCCESSFUL_ACTION:
    stdout, exit_code = remove_unsuccessful(args)
  # There can not be another value thanks to argparse validation
  print(stdout)
  sys.exit(exit_code)


if __name__ == "__main__":
  main()
