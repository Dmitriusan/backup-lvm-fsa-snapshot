import os
from datetime import datetime
from types import SimpleNamespace

from manage_backups import PATH, FILENAME, TIMESTAMP
import manage_backups


def test_should_return_limited_number_of_backups(mocker):
  """
  Checks that method splits list of backups according to time periods
  """
  args = create_args(daily_backups_max_count=2, weekly_backups_max_count=1,
                     monthly_backups_max_count=1, yearly_backups_max_count=1)
  # Configuration
  datetime_mock = mocker.patch('manage_backups.datetime')
  datetime_mock.now = mocker.Mock(return_value=datetime(2018, 11, 14, 3, 14, 1))

  list_of_backups = [
    create_entry("20170312_041112"),
    create_entry("20171114_031512"),
    create_entry("20180407_031512"),
    create_entry("20181014_031512"),
    create_entry("20181023_022501"),
    create_entry("20181106_011417"),
    create_entry("20181110_031511"),
    create_entry("20181113_031512")
  ]
  expected_number_of_chosen_backups = args.daily_backups_max_count + args.weekly_backups_max_count + \
      args.monthly_backups_max_count + args.yearly_backups_max_count


  # Run method under test
  chosen_backups = manage_backups._choose_valuable_backups(list_of_backups, args)

  assert len(chosen_backups) == expected_number_of_chosen_backups
  assert chosen_backups == [

  ]


def create_entry(datetime_str):
  timestamp = datetime.strptime(datetime_str, '%Y%m%d_%H%M%S').timestamp()
  sample_filename = "sample_file_" + datetime_str
  return {
    PATH: os.path.join("/path/to/backups", sample_filename),
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
  args.daily_backups_max_count = daily_backups_max_count
  args.weekly_backups_max_count = weekly_backups_max_count
  args.monthly_backups_max_count = monthly_backups_max_count
  args.yearly_backups_max_count = yearly_backups_max_count
  args.dry_mode = dry_mode
  return args