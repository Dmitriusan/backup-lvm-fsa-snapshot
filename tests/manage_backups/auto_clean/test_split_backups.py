import os
from datetime import datetime

from manage_backups import PATH, FILENAME, TIMESTAMP
import manage_backups


def test_should_split_backups_by_periods(mocker):
  """
  Checks that method splits list of backups according to time periods
  """
  # Configuration
  datetime_mock = mocker.patch('manage_backups.datetime')
  datetime_mock.now = mocker.Mock(return_value=datetime(2018, 11, 14, 3, 14, 1).timestamp())

  expected_yearly_backups = [
    create_entry("20171114_031512"),
  ]
  expected_monthly_backups = [
    create_entry("20170312_041112"),
  ]
  expected_weekly_backups = [
    create_entry("20181014_031512"),
  ]
  expected_daily_backups = [
    create_entry("20181110_031511"),
    create_entry("20181113_031512")
  ]
  backups = expected_yearly_backups + expected_monthly_backups + expected_weekly_backups + expected_daily_backups

  # Run method under test
  daily_backups, weekly_backups, monthly_backups, yearly_backups = manage_backups._split_backups(backups)

  # Assertions
  assert daily_backups == expected_daily_backups
  assert weekly_backups == expected_weekly_backups
  assert monthly_backups == expected_monthly_backups
  assert yearly_backups == expected_yearly_backups


def create_entry(datetime_str):
  timestamp = datetime.strptime(datetime_str, '%Y%m%d_%H%M%S').timestamp()
  sample_filename = "sample_file" + str(timestamp)
  return {
    PATH: os.path.join("/path/to/backups", sample_filename),
    FILENAME: sample_filename,
    TIMESTAMP: timestamp
  }
