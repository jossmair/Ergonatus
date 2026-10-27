from shared.profiles import ProfileStore,default_profile

def test_last_selected_profile_survives_restart(tmp_path):
    store=ProfileStore(tmp_path/'profiles.json');store.save([default_profile('A'),default_profile('B')],'B')
    other=ProfileStore(store.path);other.load();assert other.active_name=='B'

def test_corruption_recovery_is_reported_before_any_autolaunch(tmp_path):
    store=ProfileStore(tmp_path/'profiles.json');profile=default_profile('A');profile['autolaunch']=True
    store.save([profile]);store.save([profile]);store.path.write_text('broken')
    other=ProfileStore(store.path);assert other.load()[0]['autolaunch'] is True;assert other.notice
