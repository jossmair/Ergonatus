"""Per-user installer, no admin rights. Same binary provides safe uninstallation."""

import argparse
import hashlib
import json
import msvcrt
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile
import uuid
from contextlib import contextmanager
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
import winreg

REGISTRY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Transcri"
VERSION = "1.3.17"
RUN_REGISTRY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_VALUES = ("DisplayName", "DisplayVersion", "Publisher", "InstallLocation", "DisplayIcon", "UninstallString")


def resource(name):
    if getattr(sys, "frozen", False) and name in ("payload.zip", "payload.json", "uninstaller.exe"):
        external = Path(sys.executable).parent / name
        if external.is_file():
            return external
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_destination():
    return Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Transcri"


def startup_requested():
    preferences = Path(os.environ["LOCALAPPDATA"]) / "Transcri/preferences/settings.json"
    try:
        value = json.loads(preferences.read_text(encoding="utf-8")).get("autostart", True)
        return value if isinstance(value, bool) else True
    except (OSError, ValueError, AttributeError):
        return True


def menu_path():
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Transcrinator.lnk"


def registry_snapshot(key_path, names):
    values = {}
    for name in names:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                values[name] = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            values[name] = None
    return values


def snapshot_integration(work):
    menu = menu_path()
    saved = {"uninstall": registry_snapshot(REGISTRY, UNINSTALL_VALUES), "shortcuts": {}}
    if not REGISTRY.endswith("-Validation"):
        saved["run"] = registry_snapshot(RUN_REGISTRY, ("Transcri", "Transcrinator"))
    for path in (menu, menu.with_name("Transcri.lnk")):
        saved["shortcuts"][path.name] = path.exists()
        if path.exists():
            shutil.copy2(path, work / path.name)
    (work / "integration.json").write_text(json.dumps(saved), encoding="utf-8")


def restore_integration(work):
    saved = json.loads((work / "integration.json").read_text(encoding="utf-8"))
    for key_path, values in ((REGISTRY, saved["uninstall"]), (RUN_REGISTRY, saved.get("run", {}))):
        if not values:
            continue
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            for name, entry in values.items():
                if entry is None:
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(key, name, 0, entry[1], entry[0])
    for name, existed in saved["shortcuts"].items():
        path = menu_path().with_name(name)
        if existed:
            shutil.copy2(work / name, path)
        else:
            path.unlink(missing_ok=True)


def integrate(destination, previous_record):
    import pythoncom
    import win32com.client

    menu = menu_path()
    menu.parent.mkdir(parents=True, exist_ok=True)
    pythoncom.CoInitialize()
    try:
        shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(menu))
        shortcut.TargetPath = str(destination / "Transcrinator.exe")
        shortcut.WorkingDirectory = str(destination)
        shortcut.IconLocation = str(destination / "Transcrinator.exe")
        shortcut.Save()
    finally:
        shortcut = None
        pythoncom.CoUninitialize()
    legacy_menu = menu.with_name("Transcri.lnk")
    if previous_record.get("shortcut") == str(legacy_menu):
        legacy_menu.unlink(missing_ok=True)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
        for name, value in {
            "DisplayName": "Transcrinator",
            "DisplayVersion": VERSION,
            "Publisher": "Transcrinator",
            "InstallLocation": str(destination),
            "DisplayIcon": str(destination / "Transcrinator.exe"),
            "UninstallString": subprocess.list2cmdline([str(destination / "Uninstall-Transcrinator.exe"), "--uninstall"]),
        }.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    if not REGISTRY.endswith("-Validation"):
        enabled = startup_requested()
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_REGISTRY) as key:
            try:
                winreg.DeleteValue(key, "Transcri")
            except FileNotFoundError:
                pass
            if enabled:
                winreg.SetValueEx(key, "Transcrinator", 0, winreg.REG_SZ,
                                  subprocess.list2cmdline([str(destination / "Transcrinator.exe"), "--minimized"]))
            else:
                try:
                    winreg.DeleteValue(key, "Transcrinator")
                except FileNotFoundError:
                    pass


@contextmanager
def install_lock(destination):
    # Keep the lock file: unlinking it would let another updater lock a different file.
    with (destination.parent / ".Transcri-install.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("Une installation de Transcrinator est déjà en cours.") from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def write_journal(work, record):
    temporary = work / "journal.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(record, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(work / "journal.json")


def recover_update(destination, work):
    if not work.exists():
        return
    if work.is_symlink() or work.resolve() != work:
        raise RuntimeError("Dossier de récupération externe refusé.")
    if not any(work.iterdir()):
        work.rmdir()
        return
    record = json.loads((work / "journal.json").read_text(encoding="utf-8"))
    if record.get("destination") != str(destination) or record.get("schema") != 1:
        raise RuntimeError("Le dossier de récupération n’appartient pas à cette installation.")
    previous = work / "previous"
    if record.get("phase") != "committed":
        if previous.exists():
            if destination.exists():
                current = json.loads((destination / "installation.json").read_text(encoding="utf-8"))
                if current.get("transaction") != record["id"]:
                    raise RuntimeError("Installation modifiée depuis l’interruption ; récupération automatique refusée.")
                move_directory(destination, work / "aborted")
            move_directory(previous, destination)
        elif not record.get("had_previous", True) and destination.exists():
            current = json.loads((destination / "installation.json").read_text(encoding="utf-8"))
            if current.get("transaction") != record["id"]:
                raise RuntimeError("Installation modifiée depuis l’interruption ; récupération automatique refusée.")
            move_directory(destination, work / "aborted")
        if record.get("integration_started"):
            restore_integration(work)
    # Only this validated, dedicated transaction directory is removed.
    for path in work.iterdir():
        if path.name == "journal.json":
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    (work / "journal.json").unlink()
    work.rmdir()


def move_directory(source, destination):
    deadline = time.monotonic() + 15
    while True:
        try:
            source.rename(destination)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in (5, 32, 33) or time.monotonic() >= deadline:
                raise
            time.sleep(.1)


def stop_running(destination, dispatcher=None):
    import psutil

    executables = {destination / "Transcrinator.exe", destination / "Transcri.exe"}
    running = []
    for process in psutil.process_iter(["exe"]):
        try:
            if process.info["exe"] and Path(process.info["exe"]).resolve() in executables:
                running.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # The active instance can be a portable edition outside the install folder.
    # Target only this profile's instance lock, never unrelated test profiles.
    profile = Path(os.environ.get("TRANSCRI_DATA", str(Path(os.environ["LOCALAPPDATA"]) / "Transcri")))
    try:
        pid = int((profile / "cache/application.lock").read_text(encoding="utf-8").splitlines()[0])
        portable = psutil.Process(pid)
        if Path(portable.exe()).name.casefold() in ("transcrinator.exe", "transcri.exe"):
            if all(process.pid != pid for process in running):
                running.append(portable)
                running.extend(portable.children(recursive=True))
    except (OSError, ValueError, IndexError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    if not running:
        return
    binary = dispatcher or destination / (
        "Transcrinator.exe" if (destination / "Transcrinator.exe").exists() else "Transcri.exe")
    subprocess.run([str(binary), "--quit-running"], capture_output=True,
                   timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    _, alive = psutil.wait_procs(running, timeout=120)
    if alive:
        raise RuntimeError("Transcrinator est encore actif. L’ancienne version est conservée ; réessayez après sa fermeture.")


def install(destination, progress=lambda value: None):
    destination = Path(destination).resolve()
    if destination.name != "Transcri" or not destination.is_relative_to(
        Path(os.environ["LOCALAPPDATA"]).resolve()
    ):
        raise RuntimeError("Installation autorisée seulement dans le dossier dédié sous LOCALAPPDATA.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    work = destination.with_name(".Transcri-update")
    with install_lock(destination):
        recover_update(destination, work)
        receipt = destination / "installation.json"
        if destination.exists() and any(destination.iterdir()) and not receipt.exists():
            raise RuntimeError("Ce dossier contient des fichiers sans reçu d’installation Transcrinator.")
        previous_record = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        previous = previous_record.get("files", [])
        if not isinstance(previous, list) or any(not isinstance(name, str) or not
                (destination / name).resolve().is_relative_to(destination) for name in previous):
            raise RuntimeError("Ancien reçu d’installation invalide.")
        record = {"schema": 1, "id": uuid.uuid4().hex, "destination": str(destination),
                  "phase": "staging", "had_previous": destination.exists()}
        work.mkdir()
        try:
            write_journal(work, record)
            stage = work / "new"
            stage.mkdir()
            payload = resource("payload.zip")
            manifest = json.loads(resource("payload.json").read_text(encoding="utf-8"))
            if sha(payload) != manifest["sha256"]:
                raise RuntimeError("Intégrité de l’installateur invalide.")
            with zipfile.ZipFile(payload) as archive:
                entries = archive.infolist()
                names = [entry.filename for entry in entries]
                if len(set(names)) != len(names) or set(names) != set(manifest["files"]):
                    raise RuntimeError("Manifeste d’installation incohérent.")
                if shutil.disk_usage(work).free < sum(entry.file_size for entry in entries) + 256 * 2**20:
                    raise RuntimeError("Espace disque insuffisant pour installer Transcrinator avec ses modèles.")
                for index, entry in enumerate(entries):
                    target = (stage / entry.filename).resolve()
                    if not target.is_relative_to(stage) or entry.is_dir():
                        raise RuntimeError("Fichier d’installation invalide.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    if sha(target) != manifest["files"][entry.filename]:
                        raise RuntimeError("Intégrité d’un fichier invalide.")
                    progress(int((index + 1) * 85 / len(entries)))
            shutil.copy2(resource("uninstaller.exe"), stage / "Uninstall-Transcrinator.exe")
            files = names + ["Uninstall-Transcrinator.exe"]
            # Preserve unowned files; never silently replace one with a newly bundled file.
            for source in destination.rglob("*") if destination.exists() else ():
                relative = source.relative_to(destination).as_posix()
                if source.is_symlink() or not source.resolve().is_relative_to(destination):
                    raise RuntimeError("Lien externe dans le dossier d’installation ; mise à jour interrompue.")
                target = stage / relative
                if source.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif relative not in previous and relative != "installation.json":
                    if target.exists():
                        raise RuntimeError("Un fichier personnel porte le nom d’un fichier de la nouvelle version.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        os.link(source, target)
                    except OSError:
                        shutil.copy2(source, target)
            (stage / "installation.json").write_text(json.dumps({
                "version": VERSION, "files": files, "shortcut": str(menu_path()), "transaction": record["id"]
            }, indent=2), encoding="utf-8")
            snapshot_integration(work)
            stop_running(destination, stage / "Transcrinator.exe")
            record["phase"] = "ready"
            write_journal(work, record)
            if destination.exists():
                move_directory(destination, work / "previous")
            move_directory(stage, destination)
            record["integration_started"] = True
            write_journal(work, record)
            integrate(destination, previous_record)
            record["phase"] = "committed"
            write_journal(work, record)
        except BaseException:
            if (work / "journal.json").exists():
                recover_update(destination, work)
            else:
                # No staging/commit starts before the first durable journal exists.
                (work / "journal.tmp").unlink(missing_ok=True)
                work.rmdir()
            raise
        # A cleanup failure after commit does not undo a completed installation.
        # The next installer run finishes removing the validated previous copy.
        try:
            recover_update(destination, work)
        except OSError:
            pass
        progress(100)


def remove_installed_file(path):
    """Windows can retain an image/scan handle briefly after the process exits."""
    deadline = time.monotonic() + 30
    while True:
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in (5, 32, 33) or time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


def uninstall(destination):
    destination = Path(destination).resolve()
    if destination != default_destination().resolve():
        raise RuntimeError("Le dossier d’installation ne correspond pas au dossier utilisateur attendu.")
    receipt = destination / "installation.json"
    record = json.loads(receipt.read_text(encoding="utf-8"))
    running = Path(sys.executable).resolve()
    for relative in record["files"]:
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination):
            raise RuntimeError("Reçu d’installation invalide.")
        if target != running:
            remove_installed_file(target)
    menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Transcrinator.lnk"
    menu.unlink(missing_ok=True)
    receipt.unlink(missing_ok=True)
    if not REGISTRY.endswith("-Validation"):
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"
        ) as key:
            try:
                winreg.DeleteValue(key, "Transcrinator")
            except FileNotFoundError:
                pass
            try:
                winreg.DeleteValue(key, "Transcri")
            except FileNotFoundError:
                pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY)
    except FileNotFoundError:
        pass
    # Remove only empty folders; retain any user-added files.
    for path in sorted(destination.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    # Self-deletion uses one PowerShell process and literal, pre-validated absolute paths.
    if running.parent == destination and running.name == "Uninstall-Transcrinator.exe":
        quoted = str(running).replace("'", "''")
        folder = str(destination).replace("'", "''")
        script = f"Start-Sleep -Seconds 3; Remove-Item -LiteralPath '{quoted}' -Force; if (-not (Get-ChildItem -LiteralPath '{folder}')) {{ Remove-Item -LiteralPath '{folder}' }}"
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def main():
    global REGISTRY
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--self-test", type=Path)
    parser.add_argument("--self-test-install", type=Path)
    args = parser.parse_args()
    args.uninstall = args.uninstall or Path(sys.executable).name == "Uninstall-Transcrinator.exe"
    if args.self_test_install:
        if os.environ.get("TRANSCRI_INSTALLER_TEST") != "1":
            raise RuntimeError("Profil de test isolé requis.")
        REGISTRY += "-Validation"
        return self_test_install(args.self_test_install)
    if args.self_test:
        data = json.loads(resource("payload.json").read_text(encoding="utf-8"))
        args.self_test.write_text(
            json.dumps(
                {
                    "payload_integrity": sha(resource("payload.zip")) == data["sha256"],
                    "file_count": len(data["files"]),
                }
            ),
            encoding="utf-8",
        )
        return
    root = tk.Tk()
    root.title("Transcrinator — Désinstallation" if args.uninstall else f"Transcrinator {VERSION} — Installation")
    root.geometry("560x270")
    root.resizable(False, False)
    root.configure(background="#14110f")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TLabel", background="#14110f", foreground="#eee3d8", font=("Segoe UI", 10))
    style.configure("TButton", background="#ee9959", foreground="#21170f", padding=10, font=("Segoe UI", 10, "bold"))
    style.map("TButton", background=[("active", "#ffb77d")])
    style.configure("TProgressbar", background="#ef9a57", troughcolor="#352419", bordercolor="#352419")
    ttk.Label(root, text="Transcrinator", font=("Segoe UI", 22)).pack(pady=18)
    status = tk.StringVar(
        value="Fermez Transcrinator avant de désinstaller."
        if args.uninstall
        else "Installation complète hors ligne. Modèles inclus. Aucun réglage requis pour commencer."
    )
    ttk.Label(root, textvariable=status, wraplength=510).pack(pady=8)
    ttk.Label(root, text=str(default_destination()), wraplength=510).pack(pady=5)
    bar = ttk.Progressbar(root, length=500, maximum=100)
    bar.pack(pady=12)

    def action():
        button.configure(state="disabled")

        def worker():
            try:
                if args.uninstall:
                    uninstall(default_destination())
                else:
                    install(
                        default_destination(), lambda value: root.after(0, lambda: bar.configure(value=value))
                    )
                root.after(0, completed)
            except Exception as error:
                message = str(error)
                root.after(0, lambda: messagebox.showerror("Transcrinator", message))
                root.after(0, lambda: button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def completed():
        if args.uninstall:
            messagebox.showinfo(
                "Transcrinator",
                "Application supprimée. Vos modèles et préférences sont conservés dans LOCALAPPDATA/Transcri.",
            )
            root.destroy()
        else:
            subprocess.Popen([str(default_destination() / "Transcrinator.exe"), "--show"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            root.destroy()

    button = ttk.Button(root, text="Désinstaller" if args.uninstall else "Installer", command=action)
    button.pack(pady=8)
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: (
            root.destroy()
            if str(button["state"]) != "disabled"
            else messagebox.showinfo(
                "Transcrinator", "L’opération doit se terminer avant de fermer l’installateur."
            )
        ),
    )
    root.mainloop()


def self_test_install(report_path):
    destination = default_destination()
    report = {"installed": False, "application_smoke_exit": None,
              "uninstaller_present": False, "application_removed": False}
    try:
        install(destination)
        report["installed"] = (destination / "installation.json").exists()
        report["uninstaller_present"] = (destination / "Uninstall-Transcrinator.exe").exists()
        result = subprocess.run(
            [str(destination / "Transcrinator.exe"), "--smoke-test"], capture_output=True,
            timeout=90, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        report["application_smoke_exit"] = result.returncode
    except Exception as error:
        report["error_type"] = type(error).__name__
    finally:
        try:
            if (destination / "installation.json").exists():
                uninstall(destination)
            report["application_removed"] = not (destination / "Transcrinator.exe").exists()
        except Exception as error:
            report["cleanup_error_type"] = type(error).__name__
            report["cleanup_windows_error"] = getattr(error, "winerror", None)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if all((report["installed"], report["application_smoke_exit"] == 0,
                     report["uninstaller_present"], report["application_removed"])) else 1


if __name__ == "__main__":
    sys.exit(main())
