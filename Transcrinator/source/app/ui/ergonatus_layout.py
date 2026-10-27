"""Ergonatus optional layout bridge. No input hooks, clicks or model changes."""
import json
import os
from pathlib import Path
import time
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
_cache={}
_time=0
def managed_position(widget,app_id):
    global _cache,_time
    filename=os.environ.get('ERGONATUS_ORB_LAYOUT')
    if not filename:return None
    try:
        if time.monotonic()-_time>.2:
            path=Path(filename)
            if path.stat().st_size>32000:return None
            _cache=json.loads(path.read_text(encoding='utf-8'));_time=time.monotonic()
        entry=_cache.get('apps',{}).get(app_id)
        if _cache.get('version')!=1 or not isinstance(entry,dict):return None
        if widget.width()!=36 or widget.height()!=36:return None
        visible=entry.get('visible')
        if type(visible) is bool and widget.isVisible()!=visible:widget.setVisible(visible)
        pos=entry.get('position')
        if not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int or abs(v)>100000 for v in pos):return widget.pos()
        point=QPoint(*pos);screen=QApplication.screenAt(point) or QApplication.primaryScreen();area=screen.availableGeometry()
        return QPoint(max(area.left(),min(point.x(),area.right()-35)),max(area.top(),min(point.y(),area.bottom()-35)))
    except (OSError,ValueError,TypeError,AttributeError):return None
def move_group(widget,app_id):
    global _time
    name=os.environ.get('ERGONATUS_ORB_LAYOUT')
    if not name or widget.width()!=36 or widget.height()!=36:return
    try:
        path=Path(name)
        if path.stat().st_size>32000:return
        data=json.loads(path.read_text(encoding='utf-8'));entry=data.get('apps',{}).get(app_id,{})
        old=entry.get('position')
        if not isinstance(old,list) or len(old)!=2:return
        dx,dy=widget.x()-old[0],widget.y()-old[1]
        for item in data['apps'].values():
            if item.get('visible') and isinstance(item.get('position'),list):item['position']=[item['position'][0]+dx,item['position'][1]+dy]
        import uuid
        temp=path.with_name('layout-'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(data),encoding='utf-8');temp.replace(path);_time=0
    except (OSError,ValueError,TypeError,KeyError):return
