import os
from datetime import datetime

import manage_backups
from manage_backups import Backup


def test_should_put_to_buckets_by_time_periods(mocker):
  """
  Checks that method splits list of backups according to time periods
  """
  # Configuration
  datetime_mock = mocker.patch('manage_backups.datetime')
  datetime_mock.now = mocker.Mock(return_value=datetime(2018, 11, 14, 3, 14, 1))

  expected_yearly_backups = [
    create_entry("20170312_041112"),
  ]
  expected_monthly_backups = [
    create_entry("20171114_031512"),
    create_entry("20180407_031512"),
    create_entry("20181014_031512"),
  ]
  expected_weekly_backups = [
    create_entry("20181023_022501"),
    create_entry("20181106_011417"),
  ]
  expected_daily_backups = [
    create_entry("20181110_031511"),
    create_entry("20181113_031512")
  ]
  backups = expected_yearly_backups + expected_monthly_backups + expected_weekly_backups + expected_daily_backups

  # Run method under test
  daily_backups, weekly_backups, monthly_backups, yearly_backups = manage_backups._put_to_buckets_by_time_periods(backups)

  # Assertions
  assert daily_backups == expected_daily_backups
  assert weekly_backups == expected_weekly_backups
  assert monthly_backups == expected_monthly_backups
  assert yearly_backups == expected_yearly_backups


def create_entry(datetime_str):
  timestamp = datetime.strptime(datetime_str, '%Y%m%d_%H%M%S').timestamp()
  sample_filename = "sample_file_" + datetime_str
  full_path = os.path.join("/path/to/backups", sample_filename),
  return Backup(full_path, sample_filename, timestamp)
