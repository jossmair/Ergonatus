from unittest.mock import MagicMock, call, patch
import winreg

from fortinatus.windows import RUN_KEY, migrate_startup_name, set_startup, startup_enabled


def test_enabling_startup_writes_only_the_apps_named_value():
    handle = MagicMock()
    with patch.object(winreg, "CreateKey") as create, patch.object(winreg, "SetValueEx") as write, patch.object(winreg, "DeleteValue") as delete:
        create.return_value.__enter__.return_value = handle
        set_startup(True, r"C:\Profils Fortinatus")
        create.assert_called_once_with(winreg.HKEY_CURRENT_USER, RUN_KEY)
        assert write.call_args.args[:4] == (handle, "Claviernator", 0, winreg.REG_SZ)
        delete.assert_called_once_with(handle, "Fortinatus")
        assert '--config-dir "C:\\Profils Fortinatus"' in write.call_args.args[4]


def test_disabling_startup_deletes_only_the_apps_named_value():
    handle = MagicMock()
    with patch.object(winreg, "CreateKey") as create, patch.object(winreg, "DeleteValue") as delete:
        create.return_value.__enter__.return_value = handle
        set_startup(False)
        assert delete.call_args_list == [call(handle, "Claviernator"), call(handle, "Fortinatus")]


def test_old_startup_entry_is_recognized_without_enabling_a_second_entry():
    with patch.object(winreg, "OpenKey"), patch.object(winreg, "QueryValueEx", side_effect=[FileNotFoundError(), ('old.exe --minimized', winreg.REG_SZ)]):
        assert startup_enabled()


def test_startup_name_migration_preserves_command_and_does_not_enable_when_absent():
    handle = MagicMock()
    with patch.object(winreg, "OpenKey") as opened, patch.object(winreg, "QueryValueEx") as query, patch.object(winreg, "SetValueEx") as write, patch.object(winreg, "DeleteValue") as delete:
        opened.return_value.__enter__.return_value = handle
        query.side_effect = [('old.exe --minimized', winreg.REG_SZ), FileNotFoundError()]
        migrate_startup_name()
        write.assert_called_once_with(handle, "Claviernator", 0, winreg.REG_SZ, 'old.exe --minimized')
        delete.assert_called_once_with(handle, "Fortinatus")
        query.side_effect = FileNotFoundError()
        write.reset_mock()
        delete.reset_mock()
        migrate_startup_name()
        write.assert_not_called()
        delete.assert_not_called()

