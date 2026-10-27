"""Only the current user's Ergonatus startup entry is ever changed."""
import subprocess
import sys
from shared.catalog import suite_root

KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'
def command():
    return subprocess.list2cmdline([str(suite_root()/'Hub/Ergonatus.exe'),'--startup'])
def enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY) as key:return winreg.QueryValueEx(key,'Ergonatus')[0]==command()
    except FileNotFoundError:return False
def set_enabled(value):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,KEY) as key:
        if value:winreg.SetValueEx(key,'Ergonatus',0,winreg.REG_SZ,command())
        else:
            try:winreg.DeleteValue(key,'Ergonatus')
            except FileNotFoundError:pass
