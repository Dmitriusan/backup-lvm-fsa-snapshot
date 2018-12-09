from types import SimpleNamespace

import manage_backups


def test_should_build_a_sorted_list(mocker):
  """
  Checks that method lists only backup files. Other files should be skipped. List should be sorted by timestamp
  """
  # Configuration
  args = create_args()
  listdir_mock = mocker.patch('manage_backups.os.listdir')
  listdir_mock.return_value = [
    "test_.tar",
    "test__20191101_031401.tar",
    "test__20181101_031401.tar",
    "test_me__20181102_031401.tar",
    "test__20181102_031401.tar",
  ]
  isfile_mock = mocker.patch('manage_backups.os.path.isfile')
  isfile_mock.return_value = True

  # Run method under test
  result = manage_backups._list_backup_files(args)

  # Assertions
  assert result == [
    {
      'FILENAME': 'test__20181101_031401.tar',
      'PATH': '/media/backups/test__20181101_031401.tar',
      'TIMESTAMP': 1541034841.0
    },
    {
      'FILENAME': 'test__20181102_031401.tar',
      'PATH': '/media/backups/test__20181102_031401.tar',
      'TIMESTAMP': 1541121241.0
    },
    {
      'FILENAME': 'test__20191101_031401.tar',
      'PATH': '/media/backups/test__20191101_031401.tar',
      'TIMESTAMP': 1572570841.0
    }
  ]


def test_should_skip_dirs(mocker):
  """
  Checks that method skips directories even if their names follow the patter
  """
  args = create_args()
  listdir_mock = mocker.patch('manage_backups.os.listdir')
  listdir_mock.return_value = [
    "test__20181101_031401.tar",
  ]

  isfile_mock = mocker.patch('manage_backups.os.path.isfile')
  isfile_mock.return_value = False

  # Run method under test
  result = manage_backups._list_backup_files(args)

  # Assertions
  assert result == []


def create_args(backup_dest_dir='/media/backups', prefix='test', extension='.tar'):
  args = SimpleNamespace()
  args.backup_dest_dir = backup_dest_dir
  args.prefix = prefix
  args.extension = extension
  return args
