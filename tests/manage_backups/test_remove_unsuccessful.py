from types import SimpleNamespace
from manage_backups import remove_unsuccessful


def test_should_exit_cleanly_for_not_existing(mocker):
  """
  Checks that method exits with 0 exit code if target file does not exist
  """
  # Configuration
  args = create_args()
  mocker.patch('os.path.exists', new=lambda path: False)
  mocker.patch('os.remove')

  # Run method under test
  output, exit_code = remove_unsuccessful(args)

  # Assertions
  assert output == 'File /media/backups/test__20181101_031401.tar does not exist.'
  assert exit_code == 0


def test_should_error_out_on_directory(mocker):
  """
  Checks that if target file is a directory, script errors out
  """
  # Configuration
  args = create_args()
  mocker.patch('os.path.exists', new=lambda path: True)
  mocker.patch('os.path.isfile', new=lambda path: False)
  mocker.patch('os.remove')

  # Run method under test
  output, exit_code = remove_unsuccessful(args)

  # Assertions
  assert output == 'Path /media/backups/test__20181101_031401.tar points to a directory or some other non-regular file.'
  assert exit_code == 1


def test_should_error_out_if_extension_differs(mocker):
  """
  Checks that if target file name extension does not match the expected one, script errors out
  """
  # Configuration
  args = create_args(extension='tar.gz')
  mocker.patch('os.path.exists', new=lambda path: True)
  mocker.patch('os.path.isfile', new=lambda path: True)
  mocker.patch('os.remove')

  # Run method under test
  output, exit_code = remove_unsuccessful(args)

  # Assertions
  assert output == "File name test__20181101_031401.tar does not end with" \
                   " extension 'tar.gz'. Probably you specified a wrong file."
  assert exit_code == 1


def test_should_error_out_if_prefix_differs(mocker):
  """
  Checks that if target file name prefix does not match the expected one, script errors out
  """
  # Configuration
  args = create_args(prefix='wrong_prefix')
  mocker.patch('os.path.exists', new=lambda path: True)
  mocker.patch('os.path.isfile', new=lambda path: True)
  mocker.patch('os.remove')

  # Run method under test
  output, exit_code = remove_unsuccessful(args)

  # Assertions
  assert output == "File name /media/backups/test__20181101_031401.tar does not " \
                   "start with prefix 'wrong_prefix'. Probably you specified a wrong file."
  assert exit_code == 1


def test_should_error_out_if_dir_does_not_match(mocker):
  """
  Checks that if target file is located outside the backup destination dir, script errors out
  """
  # Configuration
  args = create_args(backup_dest_dir='/tmp')
  mocker.patch('os.path.exists', return_value=True)
  mocker.patch('os.path.isfile', return_value=True)
  mocker.patch('os.remove')

  # Run method under test
  output, exit_code = remove_unsuccessful(args)

  # Assertions
  assert output == "Target file is at directory /media/backups, and backup destination dir " \
                   "is /tmp. Probably you specified a wrong path."
  assert exit_code == 1


def test_should_remove_file_if_all_checks_passed(mocker):
  """
  Checks that if all checks have passed, the file is removed
  """
  # Configuration
  args = create_args()
  mocker.patch('manage_backups.os.path.exists', return_value=True)
  mocker.patch('manage_backups.os.path.isfile', return_value=True)

  remove_mock = mocker.patch('os.remove')

  # Run method under test
  output, exit_code = remove_unsuccessful(args)

  # Assertions
  assert remove_mock.called
  assert exit_code == 0


def create_args(backup_dest_dir='/media/backups', prefix='test', extension='.tar'):
  args = SimpleNamespace()
  args.backup_dest_dir = backup_dest_dir
  args.prefix = prefix
  args.extension = extension
  args.remove_file = '/media/backups/test__20181101_031401.tar'
  return args
