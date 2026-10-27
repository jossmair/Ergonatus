import json
import os
from pathlib import Path

def read_layout(app_id):
    name=os.environ.get('ERGONATUS_ORB_LAYOUT')
    if not name:return None
    path=Path(name)
    try:
        if path.stat().st_size>32000:return None
        data=json.loads(path.read_text(encoding='utf-8'))
        entry=data.get('apps',{}).get(app_id)
        if data.get('version')!=1 or not isinstance(entry,dict) or type(entry.get('visible')) is not bool:return None
        pos=entry.get('position')
        if pos is not None and (not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int or abs(v)>100000 for v in pos)):return None
        return entry
    except (OSError,ValueError,AttributeError):return None

def move_stack(app_id,position):
    name=os.environ.get('ERGONATUS_ORB_LAYOUT')
    entry=read_layout(app_id)
    if not name or not entry or entry['position'] is None:return False
    path=Path(name);data=json.loads(path.read_text(encoding='utf-8'));dx,dy=position[0]-entry['position'][0],position[1]-entry['position'][1]
    for item in data['apps'].values():
        if item.get('visible') and item.get('position') is not None:item['position']=[item['position'][0]+dx,item['position'][1]+dy]
    import uuid
    temp=path.with_name('layout-'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(data),encoding='utf-8');temp.replace(path)
    return True
