from types import SimpleNamespace
from manage_backups import auto_clean


def test_should_exit_cleanly_for_not_existing(mocker):
  """
  Checks that method exits with 0 exit code if target file does not exist
  """
  # Configuration
  args = create_args()
  mocker.patch('os.path.exists', new=lambda path: False)

  # Run method under test
  output, exit_code = auto_clean(args)

  # Assertions
  assert output == 'File /media/backups/test__20181101_031401.tar does not exist.'
  assert exit_code == 0


def create_args(backup_dest_dir='/media/backups', prefix='test', extension='.tar',
                daily_backups_max_count=7, weekly_backups_max_count=4,
                monthly_backups_max_count=6, yearly_backups_max_count=1):
  args = SimpleNamespace()
  args.backup_dest_dir = backup_dest_dir
  args.prefix = prefix
  args.extension = extension
  args.daily_backups_max_count = daily_backups_max_count,
  args.weekly_backups_max_count = weekly_backups_max_count
  args.monthly_backups_max_count = monthly_backups_max_count
  args.yearly_backups_max_count = yearly_backups_max_count
  return args
