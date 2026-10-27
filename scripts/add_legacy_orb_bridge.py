"""Optional layout hook in copied sources only. Original placement is the fallback."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BRIDGE='''"""Ergonatus optional layout bridge. No input hooks, clicks or model changes."""
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
'''
def replace_once(path,old,new):
    text=path.read_text(encoding='utf-8')
    if new in text:return
    if old not in text:raise RuntimeError('Point d’intégration absent : '+str(path))
    path.write_text(text.replace(old,new,1),encoding='utf-8')
for directory in ['Claviernator/source/fortinatus','Precisionator/source/services','Transcrinator/source/app/ui','Redactor/source/app/windows']:
    (ROOT/directory/'ergonatus_layout.py').write_text(BRIDGE,encoding='utf-8')
replace_once(ROOT/'Claviernator/source/fortinatus/keyboard_orb.py',
    '        self.orb.move(orb_position(area, self.orb.size(), companion, show_arrows))',
    '        from .ergonatus_layout import managed_position\n        managed = managed_position(self.orb, "claviernator")\n        self.orb.move(managed if managed is not None else orb_position(area, self.orb.size(), companion, show_arrows))')
replace_once(ROOT/'Precisionator/source/application.py',
    '    def position_orb(self, manual=None, screen_name=None):\n',
    '    def position_orb(self, manual=None, screen_name=None):\n        from services.ergonatus_layout import managed_position\n        managed = managed_position(self.orb, "precisionator")\n        if managed is not None and manual is None:\n            managed_screen=self.app.screenAt(managed) or self.app.primaryScreen()\n            screen_name=managed_screen.name()\n')
replace_once(ROOT/'Precisionator/source/application.py',
    '        position = choose_position([area], companions, saved, obstacles=obstacles)',
    '        position = (managed.x(),managed.y()) if managed is not None and manual is None else choose_position([area], companions, saved, obstacles=obstacles)')
replace_once(ROOT/'Transcrinator/source/app/ui/floating_hub.py',
    '    def clamp_to_screen(self, *_):\n',
    '    def clamp_to_screen(self, *_):\n        from app.ui.ergonatus_layout import managed_position\n        managed = managed_position(self, "transcrinator")\n        if managed is not None and self.drag_origin is None:\n            self.move(managed)\n            return\n')
replace_once(ROOT/'Redactor/source/app/windows/suite.py',
    'def position_orb(orb, config):\n',
    'def position_orb(orb, config):\n    from .ergonatus_layout import managed_position\n    managed = managed_position(orb, "redactor")\n    if managed is not None and getattr(orb, "start", None) is None:\n        orb.move(managed)\n        return\n')
for relative,module,key in [('Precisionator/source/ui/orb.py','services.ergonatus_layout','precisionator'),('Transcrinator/source/app/ui/floating_hub.py','app.ui.ergonatus_layout','transcrinator'),('Redactor/source/app/ui/orb.py','app.windows.ergonatus_layout','redactor')]:
    replace_once(ROOT/relative,'    def mouseReleaseEvent(self, event):\n',
        '    def mouseReleaseEvent(self, event):\n        if event.button() == Qt.LeftButton and getattr(self, "dragged", False):\n            from '+module+' import move_group\n            move_group(self, "'+key+'")\n')
print('4 adaptateurs de placement ajoutés aux copies uniquement.')
