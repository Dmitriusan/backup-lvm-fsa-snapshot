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

# Constant strings for dict
PATH = "PATH"
FILENAME = "FILENAME"
TIMESTAMP = "TIMESTAMP"
POSITION_RATING = "POSITION_RATING"
OVERALL_RATING = "OVERALL_RATING"


def configure_parser():
  parser = argparse.ArgumentParser(
    description='This script is intended for managing auto-created backup files. It can generate a filename, and '
                'auto-clean old backup files according to configured limits.',
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
  auto_clean_group.add_argument("--dry-mode", type=int, default=7,
                                help="Don't perform any actions. Just show what would be done \n")
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
  if (args.daily_backups_max_count or args.weekly_backups_max_count or
      args.monthly_backups_max_count or args.yearly_backups_max_count) \
     and not args.action == AUTO_CLEAN_ACTION:
    raise ValueError("--daily-backups-max-count, --weekly-backups-max-count, --monthly-backups-max-count, \n"
                     "and --yearly-backups-max-count arguments are only valid for action '%s'" % AUTO_CLEAN_ACTION)


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


def auto_clean(args):
  if not os.path.isdir(args.backup_dest_dir):
    msg = "Path %s is not a directory" % args.backup_dest_dir
    return msg, 1

  backups = _list_backup_files(args)
  files_to_preserve = _filter_backups_according_to_limits(backups, args)

  stdout = []
  backups_to_remove = [backup for backup in backups if backup not in files_to_preserve]
  for backup in backups_to_remove:
    if backup not in files_to_preserve:
      if args.dry_mode:
        stdout.append("Would remove old backup %s" % backup[FILENAME])
      else:
        stdout.append("Removing old backup %s" % backup[FILENAME])
        os.remove(backup[PATH])
  if not args.dry_mode:
    stdout.append("Removed %s old backup files." % len(backups_to_remove))
  return "\n".join(stdout), 0


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
    entry = {
      PATH: full_path,
      FILENAME: filename,
      TIMESTAMP: file_time.timestamp()
    }
    result.append(entry)
  return sorted(result, key=lambda item: item[TIMESTAMP])


def _filter_backups_according_to_limits(backups, args):
  """
  :param backups: source list of backups (sorted ascending by timestamps, e.g. the most recent backup is last)
  :return: a list of backups that should be preserved
  """
  # TODO: move to some other method
  # :param max_entries: the maximum number of entries that may be preserved in a list
  # :param start_timestamp: timestamp when time period starts
  # :param end_timestamp: timestamp when time period ends
  # TODO: filter each list according to periods

  result = []
  daily_backups, weekly_backups, monthly_backups, yearly_backups = _split_backups(backups)
  # TODO: sparingly balance daily, weekly and monthly backups between periods

  # TODO: cleanup lists to follow limits and distribute uniformly
  ## TODO: populate timestamps according to filename
  # entry = {
  #   "path": "",
  #   "timestamp": 4343,
  #   "position_rating": 0,
  #   "overall_rating": 0,
  # }

  return result


def _split_backups(backups):
  daily_backups = []
  weekly_backups = []
  monthly_backups = []
  yearly_backups = []
  now_timestamp = datetime.now().timestamp()
  day_millis = 24 * 3600 * 1000
  for backup in backups:
    if backup[TIMESTAMP] >= now_timestamp - 7 * day_millis:
      daily_backups.append(backup)
    elif now_timestamp - 7 * day_millis > backup[TIMESTAMP] >= now_timestamp - 31 * day_millis:
      weekly_backups.append(backup)
    elif now_timestamp - 31 * day_millis > backup[TIMESTAMP] >= now_timestamp - 365 * day_millis:
      monthly_backups.append(backup)
    elif now_timestamp - 365 * day_millis > backup[TIMESTAMP]:
      yearly_backups.append(backup)
  return daily_backups, weekly_backups, monthly_backups, yearly_backups


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
