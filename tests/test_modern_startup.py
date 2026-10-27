from pathlib import Path
from types import SimpleNamespace
import pytest
from shared.catalog import Catalog
from suite_design import lightify

def fake_pe(path):
    path.parent.mkdir(parents=True);data=bytearray(68);data[:2]=b'MZ';data[60:64]=(64).to_bytes(4,'little');data[64:]=b'PE\0\0';path.write_bytes(data)

def test_standalone_rust_apps_do_not_require_python_internal(tmp_path):
    for folder in ('Ecrinator','PDFinator'):fake_pe(tmp_path/folder/'runtime'/(folder+'.exe'))
    catalog=Catalog(tmp_path)
    assert catalog.detect('ecrinator') and catalog.detect('pdfinator')
    fake_pe(tmp_path/'Lector/runtime/Lector.exe')
    assert catalog.detect('lector') is None

def test_background_start_does_not_spawn_an_existing_process(monkeypatch,tmp_path):
    catalog=Catalog(tmp_path);monkeypatch.setattr(catalog,'detect',lambda key:tmp_path/'app.exe');monkeypatch.setattr(catalog,'running',lambda key:[SimpleNamespace(pid=123)])
    monkeypatch.setattr('shared.catalog.subprocess.Popen',lambda *a,**k:pytest.fail('Duplicate background process'))
    assert catalog.launch('transcrinator',minimized=True) is False

def test_light_surfaces_are_idempotent_and_keep_geometry():
    original='QPushButton {background:#18242A;color:#FFFFFF;border:1px solid #43545F;min-height:28px;padding:6px;}'
    styled=lightify(original)
    assert 'color:#1E3149' in styled and 'min-height:28px' in styled and 'padding:6px' in styled
    assert lightify(styled)==styled

def test_active_states_keep_their_app_identity_without_dark_panels():
    original='QPushButton#Situation:checked {background:#49344F;color:#FFFFFF;border:2px solid #B69DBB;} QPushButton:hover {background:#333333;} QPushButton#Primary {background:#444444;color:#FFFFFF;}'
    result=lightify(original,'#94418D')
    assert 'border:1px solid #94418D' in result and 'background:#94418D;color:#FFFFFF;' in result
    assert lightify(result,'#94418D')==result
