from types import SimpleNamespace
from manage_backups import _list_backup_files


def test_should_build_list(mocker):
  """
  Checks that method lists only backup files. Other files should be skipped
  """
  # Configuration
  args = create_args()
  listdir_mock = mocker.patch('os.listdir')
  listdir_mock.return_value = [
    "test_.tar.gz",
    "test__20181101_031401.tar.gz",

  ]
  isfile_mock = mocker.patch('os.path.isfile')
  isfile_mock.return_value = True

  # Run method under test
  result = _list_backup_files(args)

  # Assertions
  assert result == []


def test_should_skip_dirs(mocker):
  args = create_args()
  listdir_mock = mocker.patch('os.listdir')
  listdir_mock.return_value = [
    "test__20181101_031401.tar.gz",
  ]

  isfile_mock = mocker.patch('os.path.isfile')
  isfile_mock.return_value = False

  # Run method under test
  result = _list_backup_files(args)

  # Assertions
  assert result == []


def create_args(backup_dest_dir='/media/backups', prefix='test', extension='tar'):
  args = SimpleNamespace()
  args.backup_dest_dir = backup_dest_dir
  args.prefix = prefix
  args.extension = extension
  return args
