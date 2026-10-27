from types import SimpleNamespace
from run_ergonatus import schedule_startup
from Hub.fort_hub import HubWindow

def test_selected_apps_start_even_when_legacy_autolaunch_is_false(monkeypatch):
    calls=[]
    monkeypatch.setattr('run_ergonatus.QTimer.singleShot',lambda delay,callback:callback())
    window=SimpleNamespace(profile={'autolaunch':False,'active':['lector']},launch_selected_on_startup=lambda windows:calls.append(windows))
    schedule_startup(window)
    assert calls==[False]

def test_windows_startup_adds_windows_apps_without_duplicates(monkeypatch):
    calls=[]
    monkeypatch.setattr('Hub.fort_hub.QTimer.singleShot',lambda delay,callback:callback())
    window=SimpleNamespace(profile={'active':['lector','corrector']},startup_apps=['corrector','applinator'],launch=lambda key,minimized:calls.append((key,minimized)),arrange_orbs=lambda:None)
    HubWindow.launch_selected_on_startup(window,True)
    assert calls==[('lector',True),('corrector',True),('applinator',True)]

def test_manual_startup_only_launches_selected_apps(monkeypatch):
    calls=[]
    monkeypatch.setattr('Hub.fort_hub.QTimer.singleShot',lambda delay,callback:callback())
    window=SimpleNamespace(profile={'active':['lector']},startup_apps=['corrector'],launch=lambda key,minimized:calls.append(key),arrange_orbs=lambda:None)
    HubWindow.launch_selected_on_startup(window)
    assert calls==['lector']

def test_smoke_startup_never_launches_user_apps(monkeypatch):
    monkeypatch.setattr('run_ergonatus.QTimer.singleShot',lambda *args:(_ for _ in ()).throw(AssertionError('Unexpected startup')))
    schedule_startup(SimpleNamespace(),True,True)
