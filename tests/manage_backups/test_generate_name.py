import datetime
from types import SimpleNamespace

from manage_backups import generate_name

"""
I check everywhere stdout/sterr side effects of generate_name() method, because
the output to stdout is intended to be substituted into bash scripts 
"""


def test_name_generation(mocker):
  """
  Checks that generated filename is as expected
  """
  # Configuration
  args = create_args()
  mocker.patch('manage_backups.os.path.exists', return_value=False)
  mocker.patch('manage_backups.os.makedirs')

  stderr_mock = mocker.patch('manage_backups.sys.stderr')

  mock_time(mocker)

  # Run method under test
  generated_name, exit_code = generate_name(args)

  # Assertions
  assert generated_name == '/media/backups/test__20181101_031401.tar'
  assert exit_code == 0
  assert not stderr_mock.write.called


def test_case_existing_destination_file(mocker):
  """
  Checks that action errors out (writing to stdout) if destination file name exists
  """
  # Configuration
  args = create_args()

  mocker.patch('manage_backups.os.path.exists', return_value=True)
  makedirs_mock = mocker.patch('manage_backups.os.makedirs')
  stderr_mock = mocker.patch('manage_backups.sys.stderr')

  mock_time(mocker)

  # Run method under test
  generated_name, exit_code = generate_name(args)

  # Assertions
  assert generated_name == '/dev/null'
  assert exit_code == 1
  assert not makedirs_mock.called
  assert stderr_mock.write.call_args_list == [
    mocker.call('File /media/backups/test__20181101_031401.tar already exists\n')
  ]


def test_case_destination_dir_is_plain_file(mocker):
  """
  Checks that action errors out (writing to stdout) if backup directory path points to a plain file
  """
  # Configuration
  args = create_args()

  mocker.patch('manage_backups.os.path.exists', return_value=True)
  mocker.patch('manage_backups.os.path.isdir', return_value=False)

  makedirs_mock = mocker.patch('manage_backups.os.makedirs')
  stderr_mock = mocker.patch('manage_backups.sys.stderr')
  mock_time(mocker)

  # Run method under test
  generated_name, exit_code = generate_name(args)

  # Assertions
  assert generated_name == '/dev/null'
  assert exit_code == 1
  assert not makedirs_mock.called
  stderr_mock.write.assert_called_once_with("--backup-dest-dir argument points to existing file /media/backups "
                                            "that is not a directory\n")


def test_case_creation_of_destination_dir(mocker):
  """
  Checks that if destination dir does not exist, it's created
  """
  # Configuration
  args = create_args()

  mocker.patch('manage_backups.os.path.exists', new=lambda path: False)
  mocker.patch('manage_backups.os.path.isdir', new=lambda path: False)

  makedirs_mock = mocker.patch('manage_backups.os.makedirs')

  mock_time(mocker)

  # Run method under test
  generate_name(args)

  # Assertions
  makedirs_mock.assert_called_once_with(args.backup_dest_dir)


def create_args(backup_dest_dir='/media/backups', prefix='test', extension='.tar'):
  args = SimpleNamespace()
  args.backup_dest_dir = backup_dest_dir
  args.prefix = prefix
  args.extension = extension
  return args


def mock_time(mocker):
  datetime_mock = mocker.patch('manage_backups.datetime')
  datetime_mock.now = mocker.Mock(return_value=datetime.datetime(2018, 11, 1, 3, 14, 1))
