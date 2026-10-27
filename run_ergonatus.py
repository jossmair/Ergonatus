import argparse
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtNetwork import QLocalSocket
from Hub.fort_hub import HubWindow

def schedule_startup(window,windows_startup=False,smoke_test=False):
    if smoke_test:return
    if windows_startup:QTimer.singleShot(0,window.hide)
    QTimer.singleShot(200,lambda:window.launch_selected_on_startup(windows_startup))

def main():
    parser=argparse.ArgumentParser(description='Ergonatus · centre de contrôle local')
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--smoke-test',action='store_true')
    parser.add_argument('--snapshot',type=Path)
    parser.add_argument('--startup',action='store_true')
    args=parser.parse_args()
    if args.smoke_test:
        import os
        os.environ['ERGONATUS_TEST_MODE']='1'
    app=QApplication(sys.argv[:1]); app.setApplicationName('Ergonatus'); app.setOrganizationName('Ergonatus')
    from shared.design_bootstrap import install
    install(app)
    window=HubWindow(args.data_dir)
    if not window.manager.listening:
        socket=QLocalSocket(); socket.connectToServer(window.manager.server_name)
        if socket.waitForConnected(500):
            socket.write(b'{"version":1,"command":"show"}\n'); socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return 0
        QMessageBox.critical(None,'Ergonatus','Le service local Windows ne peut pas démarrer. '+window.manager.server.errorString())
        return 1
    window.show()
    schedule_startup(window,args.startup,args.smoke_test)
    if args.snapshot:
        def snapshot():
            args.snapshot.parent.mkdir(parents=True,exist_ok=True)
            window.grab().save(str(args.snapshot))
        QTimer.singleShot(800,snapshot)
    if args.smoke_test:
        def verify_hub():
            try:
                assert window.hub_orb.isVisible()
                window.toggle_launcher();assert window.launcher.isVisible() and len(window.launcher.tiles)==len(__import__('shared.ui.theme',fromlist=['APP_THEMES']).APP_THEMES)-1
                window.toggle_launcher();assert not window.launcher.isVisible()
                window.close()
            except Exception as error:
                print(error,file=sys.stderr);window.close();app.exit(1)
        QTimer.singleShot(1200,verify_hub)
    return app.exec()

if __name__=='__main__':
    sys.exit(main())
