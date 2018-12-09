from types import SimpleNamespace
import os
from manage_backups import auto_clean, PATH, FILENAME, TIMESTAMP


def test_should_fail_if_directory_does_not_exist(mocker):
  """
  Checks that action errors out (writing to stdout) if directory with backups does not exist
  """
  # Configuration
  args = create_args()
  isdir_mock = mocker.patch('os.path.isdir', return_value=False)

  # Run method under test
  output, exit_code = auto_clean(args)

  # Assertions
  isdir_mock.assert_called_once_with(args.backup_dest_dir)
  assert output == 'Path /media/backups is not a directory'
  assert exit_code == 1


def test_positive_flow(mocker):
  """
  Checks that method lists backups, filters this list, removes obsolete backups and exits with 0 exit code
  """
  # Configuration
  args = create_args()

  list_of_backups = [
    create_entry(args, 100),
    create_entry(args, 200),
    create_entry(args, 300),
    create_entry(args, 400),
    create_entry(args, 500),
    create_entry(args, 600),
  ]
  files_that_should_be_preserved = [
    list_of_backups[2],
    list_of_backups[4],
    list_of_backups[5]
  ]
  expected_files_for_removal = [
    list_of_backups[0],
    list_of_backups[1],
    list_of_backups[3]
  ]

  mocker.patch('manage_backups.os.path.isdir', return_value=True)
  list_backup_files_mock = mocker.patch('manage_backups._list_backup_files', return_value = list_of_backups)
  filter_backups_according_to_limits_mock = mocker.patch('manage_backups._chose_valuable_backups',
                                                         return_value=files_that_should_be_preserved)
  remove_mock = mocker.patch('manage_backups.os.remove')

  # Run method under test
  output, exit_code = auto_clean(args)

  # Assertions
  stdout_lines = output.splitlines()
  assert list_backup_files_mock.called
  assert filter_backups_according_to_limits_mock.called
  assert remove_mock.call_args_list == [
    mocker.call('/media/backups/sample_file100'),
    mocker.call('/media/backups/sample_file200'),
    mocker.call('/media/backups/sample_file400')
  ]
  assert len(stdout_lines) == len(expected_files_for_removal) + 1
  assert stdout_lines[-1] == "Removed 3 old backup files."
  assert exit_code == 0


def test_should_not_perform_actions_in_dry_mode(mocker):
  """
  Checks that in dry mode, no actual actions are done
  """
  # Configuration
  args = create_args(dry_mode=True)

  list_of_backups = [
    create_entry(args, 100),
    create_entry(args, 200),
    create_entry(args, 300),
    create_entry(args, 400),
    create_entry(args, 500),
    create_entry(args, 600),
  ]
  files_that_should_be_preserved = [
    list_of_backups[2],
    list_of_backups[4],
    list_of_backups[5]
  ]
  expected_files_for_removal = [
    list_of_backups[0],
    list_of_backups[1],
    list_of_backups[3]
  ]

  mocker.patch('manage_backups.os.path.isdir', return_value=True)
  list_backup_files_mock = mocker.patch('manage_backups._list_backup_files', return_value = list_of_backups)
  filter_backups_according_to_limits_mock = mocker.patch('manage_backups._chose_valuable_backups',
                                                         return_value=files_that_should_be_preserved)
  remove_mock = mocker.patch('manage_backups.os.remove')

  # Run method under test
  output, exit_code = auto_clean(args)

  # Assertions
  stdout_lines = output.splitlines()
  assert list_backup_files_mock.called
  assert filter_backups_according_to_limits_mock.called
  assert not remove_mock.called
  assert len(stdout_lines) == len(expected_files_for_removal)
  for line in stdout_lines:
    assert line.startswith("Would remove")
  assert exit_code == 0


def create_entry(args, timestamp):
  sample_filename = "sample_file" + str(timestamp)
  return {
    PATH: os.path.join(args.backup_dest_dir, sample_filename),
    FILENAME: sample_filename,
    TIMESTAMP: timestamp
  }


def create_args(backup_dest_dir='/media/backups', prefix='test', extension='.tar',
                daily_backups_max_count=7, weekly_backups_max_count=4,
                monthly_backups_max_count=6, yearly_backups_max_count=1,
                dry_mode=False):
  args = SimpleNamespace()
  args.backup_dest_dir = backup_dest_dir
  args.prefix = prefix
  args.extension = extension
  args.daily_backups_max_count = daily_backups_max_count,
  args.weekly_backups_max_count = weekly_backups_max_count
  args.monthly_backups_max_count = monthly_backups_max_count
  args.yearly_backups_max_count = yearly_backups_max_count
  args.dry_mode = dry_mode
  return args
