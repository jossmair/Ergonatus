import hashlib
import importlib.util
import json
import zipfile
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest


@pytest.mark.parametrize("executable,should_stop", [("Transcrinator.exe", True), ("Other.exe", False)])
def test_update_quits_the_active_portable_profile_without_touching_other_apps(
        tmp_path, monkeypatch, executable, should_stop):
    import psutil
    module = load_setup()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("TRANSCRI_DATA", raising=False)
    lock = tmp_path / "Transcri/cache/application.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("123\nTranscrinator\n")
    portable = SimpleNamespace(pid=123, exe=lambda: str(tmp_path / "portable" / executable),
                               children=lambda recursive: [])
    monkeypatch.setattr(psutil, "process_iter", lambda *args: [])
    monkeypatch.setattr(psutil, "Process", lambda pid: portable)
    waited, calls = [], []
    def wait(processes, timeout):
        waited.extend(processes)
        return processes, []
    monkeypatch.setattr(psutil, "wait_procs", wait)
    monkeypatch.setattr(module.subprocess, "run", lambda command, **kwargs: calls.append(command))
    stage = tmp_path / "stage/Transcrinator.exe"
    module.stop_running(tmp_path / "Programs/Transcri", stage)
    assert calls == ([[str(stage), "--quit-running"]] if should_stop else [])
    assert bool(waited) == should_stop


def load_setup():
    spec = importlib.util.spec_from_file_location("transcri_setup", Path("installer/setup.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_respects_disabled_windows_startup(tmp_path, monkeypatch):
    module = load_setup()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert module.startup_requested()
    preferences = tmp_path / "Transcri/preferences/settings.json"
    preferences.parent.mkdir(parents=True)
    preferences.write_text(json.dumps({"autostart": False}))
    assert not module.startup_requested()
    preferences.write_text(json.dumps({"autostart": True}))
    assert module.startup_requested()


def test_install_uninstall_preserves_user_models(tmp_path, monkeypatch):
    module = load_setup()
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    local.mkdir()
    (roaming / "Microsoft/Windows/Start Menu/Programs").mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("APPDATA", str(roaming))
    module.REGISTRY += "-Validation"
    payload = tmp_path / "payload.zip"
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("Transcrinator.exe", b"fixture executable, never launched")
    data = b"fixture executable, never launched"
    (tmp_path / "uninstaller.exe").write_bytes(b"fixture uninstaller, never launched")
    (tmp_path / "payload.json").write_text(
        json.dumps(
            {
                "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
                "files": {"Transcrinator.exe": hashlib.sha256(data).hexdigest()},
            }
        )
    )
    monkeypatch.setattr(module, "resource", lambda name: tmp_path / name)
    user_models = local / "Transcri/models/private"
    user_models.parent.mkdir(parents=True)
    user_models.write_bytes(b"keep")
    destination = module.default_destination()
    module.install(destination)
    assert (destination / "Transcrinator.exe").read_bytes() == data
    # Upgrade retires only files owned by the previous edition.
    obsolete = destination / "models/retired-engine.gguf"
    obsolete.parent.mkdir()
    obsolete.write_bytes(b"old model")
    personal = destination / "personal.txt"
    personal.write_bytes(b"keep user file")
    receipt = destination / "installation.json"
    record = json.loads(receipt.read_text(encoding="utf-8"))
    record["files"].append("models/retired-engine.gguf")
    legacy_executable = destination / "Transcri.exe"
    legacy_executable.write_bytes(b"legacy executable, never launched")
    record["files"].append("Transcri.exe")
    legacy_menu = roaming / "Microsoft/Windows/Start Menu/Programs/Transcri.lnk"
    legacy_menu.write_bytes(b"owned legacy shortcut fixture")
    record["shortcut"] = str(legacy_menu)
    receipt.write_text(json.dumps(record), encoding="utf-8")
    module.install(destination)
    assert not obsolete.exists()
    assert not legacy_executable.exists() and not legacy_menu.exists()
    assert json.loads(receipt.read_text(encoding="utf-8"))["shortcut"].endswith("Transcrinator.lnk")
    assert personal.read_bytes() == b"keep user file"
    module.uninstall(destination)
    assert personal.read_bytes() == b"keep user file"
    assert not (destination / "Transcrinator.exe").exists()
    assert user_models.read_bytes() == b"keep"


def test_install_refuses_unowned_or_external_folders(tmp_path, monkeypatch):
    module = load_setup()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    folder = tmp_path / "Transcri"
    folder.mkdir()
    (folder / "personal.txt").write_text("private")
    with pytest.raises(RuntimeError, match="sans reçu"):
        module.install(folder)
    with pytest.raises(RuntimeError, match="autorisée"):
        module.install(tmp_path / "Other")


@pytest.mark.parametrize("mode", ["success", "timeout", "failure"])
def test_self_test_always_reports_and_cleans_its_installation(tmp_path, monkeypatch, mode):
    module = load_setup()
    destination = tmp_path / "Transcri"
    destination.mkdir()
    monkeypatch.setattr(module, "default_destination", lambda: destination)

    def install(path):
        for name in ("installation.json", "Transcrinator.exe", "Uninstall-Transcrinator.exe"):
            (path / name).write_bytes(b"test fixture only")

    def launch(*args, **kwargs):
        if mode == "timeout":
            raise subprocess.TimeoutExpired("test executable", 90)
        return subprocess.CompletedProcess([], 0 if mode == "success" else 1)

    removed = []

    def uninstall(path):
        removed.append(path)
        for file in path.iterdir():
            file.unlink()

    monkeypatch.setattr(module, "install", install)
    monkeypatch.setattr(module, "uninstall", uninstall)
    monkeypatch.setattr(module.subprocess, "run", launch)
    report = tmp_path / "report.json"
    result = module.self_test_install(report)
    data = json.loads(report.read_text())
    assert result == (0 if mode == "success" else 1)
    assert data["installed"] and data["application_removed"] and removed == [destination]
    if mode == "timeout":
        assert data["error_type"] == "TimeoutExpired"


def test_uninstall_retries_a_temporary_windows_file_lock(tmp_path, monkeypatch):
    module = load_setup()
    path = tmp_path / "owned.dll"
    path.write_bytes(b"fixture")
    original = Path.unlink
    attempts = []

    def unlink(file, **kwargs):
        attempts.append(file)
        if len(attempts) < 3:
            error = PermissionError("Temporary sharing violation")
            error.winerror = 32
            raise error
        return original(file, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    module.remove_installed_file(path)
    assert len(attempts) == 3 and not path.exists()


def test_uninstall_file_lock_retry_is_bounded(tmp_path, monkeypatch):
    module = load_setup()
    path = tmp_path / "owned.dll"
    path.write_bytes(b"fixture")
    clock = iter([0, 31])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(clock))

    def unlink(file, **kwargs):
        error = PermissionError("Still used")
        error.winerror = 32
        raise error

    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(PermissionError):
        module.remove_installed_file(path)
    assert path.read_bytes() == b"fixture"


@pytest.fixture
def update_fixture(tmp_path, monkeypatch):
    from types import SimpleNamespace
    module = load_setup()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    destination = module.default_destination()
    destination.mkdir(parents=True)
    original = {"Transcrinator.exe": b"old executable fixture", "old.dll": b"old library fixture",
                "personal.txt": b"keep personal fixture"}
    for name, contents in original.items():
        (destination / name).write_bytes(contents)
    record = {"version": "old", "files": ["Transcrinator.exe", "old.dll"]}
    (destination / "installation.json").write_text(json.dumps(record), encoding="utf-8")
    original["installation.json"] = (destination / "installation.json").read_bytes()
    files = {"Transcrinator.exe": b"new executable fixture", "new.dll": b"new library fixture"}
    payload = tmp_path / "payload.zip"
    with zipfile.ZipFile(payload, "w") as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)
    manifest = {"sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
                "files": {name: hashlib.sha256(contents).hexdigest() for name, contents in files.items()}}
    manifest_path = tmp_path / "payload.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "uninstaller.exe").write_bytes(b"new uninstaller fixture")
    monkeypatch.setattr(module, "resource", lambda name: tmp_path / name)
    integration, stops = {"version": "old"}, []
    def snapshot(work):
        (work / "integration.json").write_text(json.dumps(integration), encoding="utf-8")
    def restore(work):
        integration.clear()
        integration.update(json.loads((work / "integration.json").read_text(encoding="utf-8")))
    monkeypatch.setattr(module, "snapshot_integration", snapshot)
    monkeypatch.setattr(module, "restore_integration", restore)
    monkeypatch.setattr(module, "integrate", lambda *_: integration.update(version="new"))
    monkeypatch.setattr(module, "stop_running", lambda *_: stops.append(True))
    return SimpleNamespace(module=module, destination=destination, original=original, manifest=manifest,
                           manifest_path=manifest_path, integration=integration, stops=stops,
                           work=destination.with_name(".Transcri-update"))


def assert_old_version(fixture):
    actual = {p.relative_to(fixture.destination).as_posix(): p.read_bytes()
              for p in fixture.destination.rglob("*") if p.is_file()}
    assert actual == fixture.original
    assert fixture.integration == {"version": "old"}


def test_bad_second_file_leaves_entire_old_installation_untouched(update_fixture):
    fixture = update_fixture
    fixture.manifest["files"]["new.dll"] = "0" * 64
    fixture.manifest_path.write_text(json.dumps(fixture.manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Intégrité d’un fichier"):
        fixture.module.install(fixture.destination)
    assert_old_version(fixture)
    assert not fixture.stops and not fixture.work.exists()


def test_stage_write_failure_leaves_old_version_running(update_fixture, monkeypatch):
    fixture = update_fixture
    original = fixture.module.shutil.copyfileobj
    writes = []
    def fail_second(*args, **kwargs):
        writes.append(True)
        if len(writes) == 2:
            raise OSError("synthetic disk full")
        return original(*args, **kwargs)
    monkeypatch.setattr(fixture.module.shutil, "copyfileobj", fail_second)
    with pytest.raises(OSError, match="disk full"):
        fixture.module.install(fixture.destination)
    assert_old_version(fixture)
    assert not fixture.stops and not fixture.work.exists()


def test_swap_failure_restores_complete_old_directory(update_fixture, monkeypatch):
    fixture = update_fixture
    original = fixture.module.move_directory
    def fail_swap(source, destination):
        if source == fixture.work / "new":
            raise PermissionError("synthetic locked new directory")
        return original(source, destination)
    monkeypatch.setattr(fixture.module, "move_directory", fail_swap)
    with pytest.raises(PermissionError):
        fixture.module.install(fixture.destination)
    assert_old_version(fixture)
    assert fixture.stops == [True] and not fixture.work.exists()


def test_integration_failure_rolls_back_files_receipt_and_metadata(update_fixture, monkeypatch):
    fixture = update_fixture
    def fail(*_):
        fixture.integration["version"] = "partly changed"
        raise OSError("synthetic shortcut failure")
    monkeypatch.setattr(fixture.module, "integrate", fail)
    with pytest.raises(OSError, match="shortcut"):
        fixture.module.install(fixture.destination)
    assert_old_version(fixture)
    assert not fixture.work.exists()


@pytest.mark.parametrize("phase", ["ready", "committed"])
def test_next_run_recovers_an_interrupted_directory_swap(update_fixture, phase):
    fixture = update_fixture
    fixture.work.mkdir()
    fixture.module.snapshot_integration(fixture.work)
    fixture.destination.rename(fixture.work / "previous")
    fixture.destination.mkdir()
    (fixture.destination / "Transcrinator.exe").write_bytes(b"new fixture")
    (fixture.destination / "installation.json").write_text(json.dumps({"transaction": "fixture"}))
    fixture.integration["version"] = "new"
    fixture.module.write_journal(fixture.work, {"schema": 1, "id": "fixture",
        "destination": str(fixture.destination.resolve()), "phase": phase, "integration_started": True})
    fixture.module.recover_update(fixture.destination, fixture.work)
    if phase == "ready":
        assert_old_version(fixture)
    else:
        assert (fixture.destination / "Transcrinator.exe").read_bytes() == b"new fixture"
        assert fixture.integration == {"version": "new"}
    assert not fixture.work.exists()


def test_failed_first_install_leaves_no_partial_application(update_fixture, monkeypatch):
    fixture = update_fixture
    for path in fixture.destination.iterdir():
        path.unlink()
    fixture.destination.rmdir()
    def fail(*_):
        raise OSError("synthetic integration failure")
    monkeypatch.setattr(fixture.module, "integrate", fail)
    with pytest.raises(OSError):
        fixture.module.install(fixture.destination)
    assert not fixture.destination.exists() and not fixture.work.exists()


def test_update_preserves_unowned_files_and_retires_old_owned_files(update_fixture):
    fixture = update_fixture
    fixture.module.install(fixture.destination)
    assert (fixture.destination / "personal.txt").read_bytes() == b"keep personal fixture"
    assert not (fixture.destination / "old.dll").exists()
    assert (fixture.destination / "new.dll").read_bytes() == b"new library fixture"
    record = json.loads((fixture.destination / "installation.json").read_text())
    assert record["version"] == fixture.module.VERSION and "personal.txt" not in record["files"]
    assert not fixture.work.exists()


def test_update_refuses_to_overwrite_a_personal_file_with_new_bundle_file(update_fixture):
    fixture = update_fixture
    (fixture.destination / "new.dll").write_bytes(b"personal fixture")
    fixture.original["new.dll"] = b"personal fixture"
    with pytest.raises(RuntimeError, match="personnel"):
        fixture.module.install(fixture.destination)
    assert_old_version(fixture)
    assert not fixture.stops


def test_two_installers_cannot_update_together(update_fixture):
    fixture = update_fixture
    with fixture.module.install_lock(fixture.destination):
        with pytest.raises(RuntimeError, match="déjà en cours"):
            fixture.module.install(fixture.destination)
    assert_old_version(fixture)


def test_unknown_recovery_directory_is_preserved(update_fixture):
    fixture = update_fixture
    fixture.work.mkdir()
    (fixture.work / "personal.txt").write_bytes(b"do not delete")
    with pytest.raises(FileNotFoundError):
        fixture.module.install(fixture.destination)
    assert (fixture.work / "personal.txt").read_bytes() == b"do not delete"
    assert_old_version(fixture)


def test_committed_cleanup_failure_keeps_journal_for_next_run(update_fixture, monkeypatch):
    fixture = update_fixture
    original = fixture.module.shutil.rmtree
    def fail_previous(path, *args, **kwargs):
        if Path(path) == fixture.work / "previous":
            raise PermissionError("synthetic scan lock")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(fixture.module.shutil, "rmtree", fail_previous)
    fixture.module.install(fixture.destination)
    assert (fixture.work / "journal.json").exists()
    assert json.loads((fixture.work / "journal.json").read_text())["phase"] == "committed"
    assert (fixture.destination / "new.dll").exists()
    monkeypatch.setattr(fixture.module.shutil, "rmtree", original)
    fixture.module.recover_update(fixture.destination, fixture.work)
    assert not fixture.work.exists() and (fixture.destination / "new.dll").exists()


def test_initial_journal_failure_leaves_no_stale_transaction(update_fixture, monkeypatch):
    fixture = update_fixture
    def fail(*_):
        raise OSError("synthetic disk full")
    monkeypatch.setattr(fixture.module, "write_journal", fail)
    with pytest.raises(OSError):
        fixture.module.install(fixture.destination)
    assert_old_version(fixture)
    assert not fixture.work.exists()
