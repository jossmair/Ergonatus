import json
from pathlib import Path
import struct
import pytest
from app.ai.engine import ReasoningFilter
from app.ai.gguf import metadata, luciole_template
from app.ai.model_manager import validate_model, download_model, CATALOG
from app.ai.prompts import Request
from app.config import Config
from app.integration.fortinator import envelope, validate_envelope
from app.security.validation import FrameDecoder, encode_frame, parse_json, splice_text, validate_command
from app.windows.hotkeys import parse_hotkey


@pytest.mark.parametrize("chunks,expected", [
    (["Bonjour"], "Bonjour"),
    (["<thi", "nk>raisonnement", "</thi", "nk>Texte final"], "Texte final"),
    (["Texte <", "think>secret", "</think> visible"], "Texte  visible"),
    (["<think>jamais fermé"], ""),
    (["Un < pas une balise"], "Un < pas une balise"),
])
def test_reasoning_stream(chunks, expected):
    parser = ReasoningFilter()
    assert "".join(parser.feed(c) for c in chunks) + parser.feed("", final=True) == expected


def test_frame_fragmentation_and_coalescing():
    payloads = [{"text": "Éloïse"}, {"command": "status"}]
    data = b"".join(encode_frame(p) for p in payloads)
    parser, found = FrameDecoder(), []
    for byte in data:
        found.extend(parser.feed(bytes([byte])))
    assert found == payloads
    assert FrameDecoder().feed(data) == payloads


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'{"x":{"a":1,"a":2}}', b'[]', b'{"a":NaN}', b'\xff\xff'])
def test_json_rejects_unsafe_inputs(data):
    with pytest.raises((ValueError, UnicodeError)):
        parse_json(data)


def test_frame_limits():
    for size in (0, 1, 65537, 0xffffffff):
        with pytest.raises(ValueError):
            FrameDecoder().feed(struct.pack("<I", size))


def test_depth_limit():
    with pytest.raises(ValueError):
        parse_json((('{"x":' * 18) + '0' + ('}' * 18)).encode())


@pytest.mark.parametrize("command", ["insert", "send", "paste", "click", "execute", "lifecycle.shutdown"])
def test_external_writes_are_absent(command):
    with pytest.raises(ValueError):
        validate_command({"command": command})


def test_external_draft_validation():
    assert validate_command({"command": "compose", "text": "Un mail", "style": "Naturel"})
    for payload in ({"command": "status", "text": "secret"}, {"command": "compose", "path": "evil.exe"},
                    {"command": "compose", "text": "x" * 24001}, {"command": "compose", "style": "unknown"}):
        with pytest.raises(ValueError): validate_command(payload)


def test_supervision_envelope():
    message = envelope("Status", {})
    assert validate_envelope(message) == message
    with pytest.raises(ValueError): validate_envelope({**message, "version": True})
    with pytest.raises(ValueError): validate_envelope({**message, "module": "claviernator"})


def test_insertion_preserves_surrounding_text():
    assert splice_text("Avant. fautes. Après.", 7, 14, "fautes.", "Corrigé.") == "Avant. Corrigé. Après."
    assert splice_text("Éloïse 🖋 fin", 8, 8, "", "ici ") == "Éloïse 🖋ici  fin"


def test_changed_selection_and_invalid_ranges_never_write():
    for start, end, selected in ((0, 4, "other"), (-1, 0, ""), (2, 1, ""), (0, 99, ""), (False, 1, "x")):
        with pytest.raises(ValueError): splice_text("texte", start, end, selected, "nouveau")


def test_prompts_require_nonempty_text_and_known_action():
    with pytest.raises(ValueError): Request("correct", " ").messages()
    with pytest.raises(ValueError): Request("insert", "texte").messages()
    assert "Style" not in Request("correct", "texte").messages()[-1]["content"]


@pytest.mark.parametrize("shortcut", ["R", "Shift+R", "Ctrl+Ctrl+R", "Ctrl+DELETE", "Ctrl+F25"])
def test_non_intrusive_shortcuts(shortcut):
    with pytest.raises(ValueError): parse_hotkey(shortcut)


def test_config_and_shortcuts(tmp_path, monkeypatch):
    monkeypatch.setenv("REDACTOR_DATA_DIR", str(tmp_path))
    config = Config(animation="none", hotkey="Alt+F8", text_size=16)
    config.save()
    assert Config.load()[0] == config
    assert parse_hotkey("") is None
    assert parse_hotkey("Ctrl+Alt+R") == (0x4003, ord("R"))
    (tmp_path / "settings.json").write_text('{"threads":true}', encoding="utf-8")
    restored, notice = Config.load()
    assert restored == Config() and notice
    assert (tmp_path / "settings.json").read_text() == '{"threads":true}'


def test_gguf_validation_and_no_implicit_download(tmp_path):
    path = tmp_path / "bad.gguf"
    path.write_bytes(b"not a model" * 200)
    with pytest.raises(ValueError): validate_model(path)
    with pytest.raises(PermissionError): download_model(CATALOG[0], tmp_path, consent=False)
    with pytest.raises(ValueError): metadata(path)


def test_luciole_generation_tags_are_transparent():
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    template = "A{% generation %}{{ 'B' }}{% endgeneration %}C"
    assert ImmutableSandboxedEnvironment().from_string(luciole_template(template)).render() == "\nABC"
