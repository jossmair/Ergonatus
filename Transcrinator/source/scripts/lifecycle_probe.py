"""Validate the frozen app, actual model readiness and single-instance commands."""
import json
import os
from pathlib import Path
import subprocess
import time
from PIL import Image

from app import __version__


def main():
    root = Path(__file__).resolve().parents[1]
    executable = root / f"dist/Transcrinator-{__version__}/Transcrinator.exe"
    tag = __version__.replace(".", "")
    profile = root / f"build/lifecycle-{tag}-profile"
    report_path = root / f"docs/validation/lifecycle-{tag}.json"
    snapshot = root / f"docs/validation/packaged-{tag}.png"
    env = os.environ.copy()
    env["TRANSCRI_DATA"] = str(profile)
    env.pop("TRANSCRI_BUNDLE", None)
    flags = {"env": env, "creationflags": subprocess.CREATE_NO_WINDOW}
    report = {}
    started = time.monotonic()
    ready = subprocess.run([str(executable), "--ui-snapshot", str(snapshot)], timeout=65, **flags)
    report["actual_model_ready_and_normal_exit"] = ready.returncode == 0 and snapshot.is_file()
    if not report["actual_model_ready_and_normal_exit"]:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise RuntimeError("Le binaire n’a pas atteint l’état Prêt.")
    with Image.open(snapshot) as picture:
        corners = [picture.getpixel(point)[3] for point in (
            (0, 0), (picture.width - 1, 0), (0, picture.height - 1),
            (picture.width - 1, picture.height - 1))]
    report["all_four_corners_transparent"] = corners == [0, 0, 0, 0]
    ui = json.loads(snapshot.with_name(snapshot.stem + "-ui.json").read_text())
    report["hub_visible_when_ready"] = ui["hub_visible"] and ui["hub_state"] == "Prêt"
    report["transcript_panel_removed"] = ui["transcript_panel_absent"]
    report["saved_trigger_available"] = ui["trigger_key"] == "shift_left"
    report["numbers_switch_defaults_to_digits"] = ui["number_toggle_checked"]
    report["compact_window"] = ui["main_window_size"][0] <= 680 and ui["main_window_size"][1] <= 550
    report["all_options_visible"] = ui["options_fully_visible"]
    report["renamed_transcrinator"] = ui["application_name"] == "Transcrinator"
    report["compact_key_menu_with_transparent_corners"] = (
        ui["trigger_menu_saved"] and ui["trigger_menu_transparent"] and ui["trigger_menu_compact"])
    report["painted_caption_icons"] = ui["caption_icons"]
    report["dictionary_close_button"] = ui["dictionary_saved"] and ui["dictionary_closed_without_saving"]
    report["processing_stream_animated_without_microphone_energy"] = (
        ui["processing_saved"] and ui["processing_animated"] and ui["processing_without_microphone_energy"])
    if "screen" in ui:
        x, y, width, height = ui["screen"]
        normal_x, normal_y = ui["normal_position"]
        compact_x, compact_y = ui["compact_position"]
        report["hub_centered_on_cursor_screen"] = abs(normal_x + 86 - (x + width / 2)) <= .5 and normal_y + 44 == y + height - 16
        report["idle_halo_bottom_right"] = (ui["compact_saved"] and ui["compact_size"] == [36, 36]
                                            and compact_x + 36 == x + width - 16
                                            and compact_y + 36 == y + height - 16)
        report["restored_on_dictation_preparation"] = ui["restored_on_preparation"]
        report["idle_disk_animated"] = ui.get("compact_animated", False)
        report["activation_and_speech_captured"] = ui.get("activation_saved", False) and ui.get("speech_saved", False)
    report["load_snapshot_and_shutdown_seconds"] = round(time.monotonic() - started, 3)
    process = subprocess.Popen([str(executable), "--minimized"], **flags)
    try:
        lock = profile / "cache/application.lock"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Application stopped before acquiring its lock")
            if lock.is_file() and lock.read_text(encoding="utf-8").splitlines()[0] == str(process.pid):
                break
            time.sleep(.1)
        else:
            raise RuntimeError("Application lock not acquired")
        duplicate = subprocess.run([str(executable), "--show"], timeout=12, **flags)
        report["duplicate_opens_existing_instance"] = duplicate.returncode == 0 and process.poll() is None
        request = subprocess.run([str(executable), "--quit-running"], timeout=12, **flags)
        report["graceful_quit_command"] = request.returncode == 0
        report["normal_exit_after_quit"] = process.wait(timeout=30) == 0
        report["lock_released"] = not lock.exists()
    finally:
        if process.poll() is None:
            subprocess.run([str(executable), "--quit-running"], timeout=12, **flags)
            process.wait(timeout=30)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    assert all(value for value in report.values())


if __name__ == "__main__":
    main()
