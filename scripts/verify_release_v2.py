"""Test only disposable app instances with isolated data and no live input aids."""
from pathlib import Path
import os,sys,json,subprocess,time,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['ERGONATUS_DATA']=str(ROOT/'.test-data'/('release-v2-'+uuid.uuid4().hex))
os.environ['ERGONATUS_NO_HOTKEYS']='1'
os.environ['USERDOMAIN']='ErgonatusReleaseTest-'+uuid.uuid4().hex
from shared.ui.theme import APP_THEMES
from shared.apps.base import instance_name
from shared.catalog import Catalog
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint
from PySide6.QtNetwork import QLocalSocket
from orb_manager.manager import selected_stack
import win32gui,win32process
app=QApplication([]);environment=os.environ.copy();reports=[]
for key,item in APP_THEMES.items():
    if key in ('ergonatus','claviernator','precisionator','transcrinator','redactor'):continue
    path=ROOT/item['folder']/'runtime'/(item['folder']+'.exe');started=time.monotonic()
    result=subprocess.run([str(path),'--smoke-test','--snapshot',str(ROOT/'docs/validation'/f'{key}-packaged.png')],env=environment,capture_output=True,timeout=25)
    state=Path(environment['ERGONATUS_DATA'])/key/'window.json'
    record=dict(app=key,exit_code=result.returncode,seconds=round(time.monotonic()-started,3),window_state_written=state.is_file());reports.append(record);print(json.dumps(record),flush=True)
    if result.returncode:raise RuntimeError('Échec du paquet : '+key)
    if not state.is_file():raise RuntimeError('Position non enregistrée : '+key)
(ROOT/'docs/validation/satellites-packaged.json').write_text(json.dumps(reports,indent=2))

order=['corrector','calculinator','lector'];screen=app.primaryScreen();positions=selected_stack(screen.availableGeometry(),order)
layout=ROOT/'.test-data/release-v2-layout.json';layout.write_text(json.dumps(dict(version=1,apps={key:dict(visible=True,position=position) for key,position in zip(order,positions)})))
environment['ERGONATUS_ORB_LAYOUT']=str(layout);children={}
def send(key,command):
    socket=QLocalSocket();socket.connectToServer(instance_name(key))
    if not socket.waitForConnected(1500):raise RuntimeError('IPC non connecté : '+key)
    socket.write((json.dumps(dict(version=1,command=command))+'\n').encode());socket.waitForBytesWritten(1000)
    socket.waitForReadyRead(1000);reply=bytes(socket.readAll());socket.disconnectFromServer()
    return b'true' in reply
try:
    for key in order:children[key]=subprocess.Popen([str(Catalog().detect(key)),'--minimized'],env=environment)
    native={}
    for _ in range(100):
        app.processEvents();time.sleep(.1);native={}
        def observe(hwnd,_):
            pid=win32process.GetWindowThreadProcessId(hwnd)[1]
            key=next((key for key,process in children.items() if process.pid==pid),None)
            if key and 'orbe' in win32gui.GetWindowText(hwnd).casefold() and win32gui.IsWindowVisible(hwnd):
                x,y,r,b=win32gui.GetWindowRect(hwnd);native[key]=dict(hwnd=hwnd,rect=[x,y,r-x,b-y])
        win32gui.EnumWindows(observe,None)
        if len(native)==3 and len({item['rect'][0] for item in native.values()})==1 and _>=10:break
    print('Native stack: '+json.dumps(native),flush=True)
    print('Child exit codes: '+json.dumps({key:process.poll() for key,process in children.items()}),flush=True)
    expected=round(36*screen.devicePixelRatio())
    assert len(native)==3 and all(item['rect'][2:]==[expected,expected] for item in native.values()),native
    assert len({item['rect'][0] for item in native.values()})==1
    ys=[native[key]['rect'][1] for key in order]
    assert ys[0]>ys[1]>ys[2]
    assert send('lector','orb_hide');time.sleep(.6)
    assert not win32gui.IsWindowVisible(native['lector']['hwnd'])
    assert send('lector','orb_show');time.sleep(.2)
    assert win32gui.IsWindowVisible(native['lector']['hwnd'])
    report=dict(logical_size=36,dpr=screen.devicePixelRatio(),native=native,stacked=True,hide_show=True)
    (ROOT/'docs/validation/orbs-36-native.json').write_text(json.dumps(report,indent=2));print('Pile native 36 px, masquage et affichage : OK',flush=True)
finally:
    for key,process in children.items():
        if process.poll() is None:
            try:send(key,'quit')
            except RuntimeError as error:print(str(error),flush=True)
    for process in children.values():assert process.wait(timeout=20)==0
