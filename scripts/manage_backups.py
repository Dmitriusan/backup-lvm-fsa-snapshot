#!/usr/bin/env python3

import argparse
import os
import sys
from datetime import datetime

GENERATE_NAME_ACTION = 'generate-name'
AUTO_CLEAN_ACTION = 'auto-clean'
REMOVE_UNSUCCESSFUL_ACTION = 'remove-unsuccessful'
DATE_STRING_FORMAT = '%Y%m%d_%H%M%S'


# TODO: add action to create a symlink to a latest backup


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

  generate_name_group = parser.add_argument_group('Options for a "%s" action' % GENERATE_NAME_ACTION,
                                                  'File name generation for a backup file')

  auto_clean_group = parser.add_argument_group('Options for an "%s" action' % AUTO_CLEAN_ACTION,
                                               'Auto-clean old backup files')
  auto_clean_group.add_argument("--dry-mode", type=int, default=7,
                                help="Don't perform any actions. Just show what would be done \n")
  auto_clean_group.add_argument("--daily-backups-max-count", type=int, default=7,
                                help="How many daily backups should be stored at the location specified by \n"
                                     "--backup-dest-dir . Older backups from this week are removed. The default \n"
                                     "value is 5. \n")
  auto_clean_group.add_argument("--weekly-backups-max-count", type=int, default=4,
                                help="How many latest weekly backups should be stored at the location specified by \n"
                                     "--backup-dest-dir . Older weekly backups are removed. The default "
                                     "value is 2.")
  auto_clean_group.add_argument("--monthly-backups-max-count", type=int, default=12,
                                help="How many latest monthly backups should be stored at the location specified by \n"
                                     "--backup-dest-dir . Older monthly backups are removed. The default value is 1.")
  auto_clean_group.add_argument("--yearly-backups-max-count", type=int, default=3,
                                help="How many latest yearly backups should be stored at the location specified by \n"
                                     "--backup-dest-dir . Older yearly backups are removed. The default value is 0.")

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
    raise ValueError("--remove-file option is valid only for action '%s'" % REMOVE_UNSUCCESSFUL_ACTION)
  # TODO: add other restrictions


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

  if os.path.exists(args.backup_dest_dir) and not os.path.isdir(args.backup_dest_dir):
    error = "--backup-dest-dir argument points to existing file %s that is not a directory\n" % args.backup_dest_dir

  if error:
    full_path = "/dev/null"  # a safeguard against breaking substitution logic at shell scripts
    sys.stderr.write(error)
    return full_path, 1

  if not os.path.exists(args.backup_dest_dir):
    os.makedirs(args.backup_dest_dir)

  return full_path, 0


def auto_clean(args):
  # TODO: add dry mode
  # TODO: if the dest directory does not exist, exit
  # TODO: print stats on backup files
  # TODO: sparingly balance daily, weekly and monthly backups between periods

  # TODO: populate list of backups
  ## TODO: populate timestamps according to filename
  entry = {
    "path": "",
    "timestamp": 4343,
    "position_rating": 0,
    "overall_rating": 0,
  }
  backups = []

  # TODO: fix syntax
  daily_backups = []
  weekly_backups = []
  monthly_backups = []
  yearly_backups = []
  for backup in backups:
    if backup["date"] >= now - 7:
      daily_backups.append(backup)
    elif now - 7 > backup["date"] >= now - 31:
      weekly_backups.append(backup)
    elif now - 31 > backup["date"] >= now - 365:
      monthly_backups.append(backup)
    elif now - 365 > backup["date"]:
      yearly_backups.append(backup)

  # TODO: filter each list according to periods
  # TODO: remove

  # TODO: cleanup lists to follow limits and distribute uniformly

  # TODO: instead of these src lists, add filtered lists
  files_to_preserve = daily_backups + weekly_backups + monthly_backups + yearly_backups
  for backup in backups:
    if backup not in files_to_preserve:
      print("Removing old backup %s" % backup)
      os.remove(backup["path"])


def filter_list_according_to_limit(src_list, max_entries, start_timestamp, end_timestamp):
  """

  :param src_list: source list of backups
  :param max_entries: the maximum number of entries that may be preserved in a list
  :param start_timestamp: timestamp when time period starts 
  :param end_timestamp: timestamp when time period ends
  :return: a list of backups that should be preserved
  """
  result = []

  return result


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
  if args.action == GENERATE_NAME_ACTION:
    generated_name, exit_code = generate_name(args)
    print(generated_name)
  elif args.action == AUTO_CLEAN_ACTION:
    generated_name, exit_code = auto_clean(args)
  elif args.action == REMOVE_UNSUCCESSFUL_ACTION:
    output, exit_code = remove_unsuccessful(args)
    print(output)
  # There can not be another value thanks to argparse validation
  sys.exit(exit_code)


if __name__ == "__main__":
  main()
