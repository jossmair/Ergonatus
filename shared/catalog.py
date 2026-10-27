from pathlib import Path
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
import psutil
from shared.ui.theme import APP_THEMES

def suite_root():
    if not getattr(sys,'frozen',False):return Path(__file__).resolve().parents[1]
    for candidate in Path(sys.executable).resolve().parents:
        if (candidate/'assets/orbs/ergonatus.png').is_file() and (candidate/'Hub').is_dir():return candidate
    raise RuntimeError('Le dossier partagé Ergonatus est introuvable. Conservez la suite complète.')

def valid_executable(path):
    """Bounded local PE validation, ported from Fortinator ExecutablePolicy."""
    path = Path(path)
    if not path.is_absolute() or str(path).startswith('\\\\') or path.suffix.lower() != '.exe':
        return False
    try:
        if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (path, *path.parents)):
            return False
        with path.open('rb') as stream:
            header = stream.read(64)
            if len(header) < 64 or header[:2] != b'MZ':
                return False
            offset = struct.unpack_from('<I', header, 60)[0]
            if offset > path.stat().st_size - 4:
                return False
            stream.seek(offset)
            return stream.read(4) == b'PE\0\0'
    except OSError:
        return False

class Catalog:
    def __init__(self, root=None):
        self.root = Path(root or suite_root()).resolve()
        self.processes = {}
        self.errors = {}
        self.requests = []
        self._running_by_path={};self._scan_time=0;self._username=psutil.Process().username();self._detected={};self._background_native={}

    def detect(self, app_id):
        if app_id not in APP_THEMES or app_id == 'ergonatus':
            return None
        item = APP_THEMES[app_id]
        target = self.root / item['folder'] / 'runtime' / (item['folder'] + '.exe')
        cached=self._detected.get(app_id)
        if cached and time.monotonic()-cached[0]<3:return cached[1]
        # Écrinator/PDFinator are now native standalone Rust applications.
        detected=target if valid_executable(target) and ((target.parent/'_internal').is_dir() or app_id in ('ecrinator','pdfinator')) else None
        self._detected[app_id]=(time.monotonic(),detected)
        return detected

    def running(self, app_id):
        path = self.detect(app_id)
        if path is None:
            return []
        if time.monotonic()-self._scan_time<1:return self._running_by_path.get(path,[])
        found={}
        for p in psutil.process_iter(['pid', 'exe', 'create_time', 'username']):
            try:
                if p.info['exe'] and p.info['username']==self._username and os.path.normcase(p.info['exe']).startswith(os.path.normcase(str(self.root)+os.sep)):
                    # Process image paths are already absolute. Resolving every
                    # Windows process path performs unnecessary filesystem I/O.
                    found.setdefault(Path(p.info['exe']),[]).append(p)
            except (psutil.Error, OSError):
                continue
        self._running_by_path=found;self._scan_time=time.monotonic()
        return found.get(path,[])

    def launch(self, app_id,minimized=False):
        path = self.detect(app_id)
        if path is None:
            raise ValueError('Logiciel non livré : aucun lancement disponible.')
        # Existing instances own their input hooks. Never start a second copy knowingly.
        if self.running(app_id):
            if minimized:return False
            if app_id in ('ecrinator','pdfinator'):
                self.reveal_native(app_id);return False
            args=[str(path)]+(['--settings'] if app_id=='precisionator' else [])
            self.requests.append(subprocess.Popen(args,cwd=path.parent,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
            return False
        env = os.environ.copy()
        env['TRANSCRI_BUNDLE'] = str(self.root / 'ergoai' / 'transcription')
        env['ERGONATUS_ORB_LAYOUT']=str(getattr(self,'layout_path',self.root/'orb_manager/live-layout.json'))
        env['ERGONATUS_SHARED_AI']='1'
        env['ERGONATUS_BACKGROUND_START']='1' if minimized else '0'
        args = [str(path)]
        if app_id == 'redactor':
            args += ['--link-suite']
        if minimized and app_id not in ('precisionator','ecrinator','pdfinator'):
            args += ['--minimized']
        elif app_id=='precisionator' and not minimized:args+=['--settings']
        startupinfo=None
        if minimized and app_id in ('ecrinator','pdfinator') and os.name=='nt':
            startupinfo=subprocess.STARTUPINFO();startupinfo.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startupinfo.wShowWindow=7
        p = subprocess.Popen(args, cwd=path.parent, env=env, startupinfo=startupinfo, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.processes[app_id] = p
        if minimized and app_id in ('ecrinator','pdfinator'):self._background_native[app_id]=p.pid
        self.errors.pop(app_id, None)
        return True

    def reveal_native(self,app_id):
        self._background_native.pop(app_id,None)
        import win32gui,win32process,win32con
        pids={p.pid for p in self.running(app_id)}
        def reveal(hwnd,_):
            if win32process.GetWindowThreadProcessId(hwnd)[1] in pids and win32gui.GetWindowText(hwnd):
                win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
                try:win32gui.SetForegroundWindow(hwnd)
                except Exception:pass
        win32gui.EnumWindows(reveal,None)

    def settle_native_background(self):
        if not self._background_native:return
        import win32gui,win32process,win32con
        pending=dict(self._background_native)
        def settle(hwnd,_):
            pid=win32process.GetWindowThreadProcessId(hwnd)[1]
            for key,expected in pending.items():
                if pid==expected and win32gui.GetWindowText(hwnd) and win32gui.IsWindowVisible(hwnd):
                    win32gui.ShowWindow(hwnd,win32con.SW_SHOWMINNOACTIVE);self._background_native.pop(key,None)
        win32gui.EnumWindows(settle,None)

    def stop(self, app_id):
        if app_id in ('ecrinator','pdfinator'):
            import win32gui,win32process,win32con
            pids={p.pid for p in self.running(app_id)}
            def close(hwnd,_):
                if win32process.GetWindowThreadProcessId(hwnd)[1] in pids and win32gui.GetWindowText(hwnd):win32gui.PostMessage(hwnd,win32con.WM_CLOSE,0,0)
            win32gui.EnumWindows(close,None);return bool(pids)
        if app_id in ('claviernator','precisionator','redactor') or app_id not in APP_THEMES:
            raise ValueError('Utilisez Quitter dans le menu du logiciel : arrêt distant non pris en charge.')
        if not self.running(app_id):
            return False
        env = os.environ.copy()
        env['TRANSCRI_BUNDLE'] = str(self.root / 'ergoai' / 'transcription')
        p = subprocess.Popen([str(self.detect(app_id)), '--quit-running'], env=env,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.requests.append(p)
        return True

    def quit_suite(self):
        """Request normal shutdown only for this user's exact suite executables."""
        from PySide6.QtNetwork import QLocalSocket
        from shared.apps.base import instance_name
        native_pids=set();standalone_pids=set();self._scan_time=0
        for key in APP_THEMES:
            if key=='ergonatus':continue
            processes=self.running(key)
            if not processes:continue
            if key in ('ecrinator','pdfinator'):
                standalone_pids.update(p.pid for p in processes)
            elif key in ('claviernator','precisionator','transcrinator','redactor'):
                native_pids.update(p.pid for p in processes)
            else:
                socket=QLocalSocket();socket.connectToServer(instance_name(key))
                if socket.waitForConnected(300):
                    socket.write(b'{"version":1,"command":"quit"}\n');socket.waitForBytesWritten(500);socket.disconnectFromServer()
        if native_pids or standalone_pids:
            import win32gui,win32process,win32api,win32con
            threads=set()
            def collect(hwnd,_):
                thread,pid=win32process.GetWindowThreadProcessId(hwnd)
                if pid in native_pids:threads.add(thread)
                if pid in standalone_pids and win32gui.GetWindowText(hwnd):win32gui.PostMessage(hwnd,win32con.WM_CLOSE,0,0)
            win32gui.EnumWindows(collect,None)
            for thread in threads:
                try:win32api.PostThreadMessage(thread,win32con.WM_QUIT,0,0)
                except OSError:pass

    def poll(self):
        self.requests = [p for p in self.requests if p.poll() is None]
        for app_id, p in list(self.processes.items()):
            status = p.poll()
            if status is not None:
                if status:
                    self.errors[app_id] = 'Le logiciel a quitté avec une erreur.'
                del self.processes[app_id]

    def state(self, app_id, enabled=False):
        if app_id == 'ergonatus':
            return 'Hub ouvert'
        if app_id in self.errors:
            return 'Erreur'
        if not self.detect(app_id):
            return 'À développer · non livré'
        if self.running(app_id):
            return 'En cours · Orb native'
        return 'Activé · prêt à ouvrir' if enabled else 'Installé · désactivé'
