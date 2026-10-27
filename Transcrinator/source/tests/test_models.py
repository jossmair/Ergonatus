import hashlib

import httpx
import pytest

from app.services.model_manager import Artifact, ModelManager
from app.core.device_detector import Hardware
from app.services.engine_manager import choose_backend


def test_retired_engines_are_rejected():
    hw = Hardware("test", 4, 16 * 2**30, 8 * 2**30)
    for engine in ("nemotron", "voxtral"):
        with pytest.raises(RuntimeError, match="uniquement Parakeet Ultra"):
            choose_backend(engine, "cpu", hw)


def test_absent_runtime_is_explicit(monkeypatch):
    monkeypatch.setattr("app.services.engine_manager.runtime_file", lambda *args: None)
    hw = Hardware("test", 4, 16 * 2**30, 8 * 2**30)
    with pytest.raises(RuntimeError, match="absent"):
        choose_backend("parakeet", "cpu", hw)


def test_checksum_refuses_corruption(tmp_path):
    artifact = Artifact("a", "https://unused", 3, hashlib.sha256(b"abc").hexdigest(), "MIT")
    part = tmp_path / "a.part"
    part.write_bytes(b"bad")
    with pytest.raises(RuntimeError, match="Intégrité"):
        ModelManager.download(artifact, tmp_path / "a")
    assert not (tmp_path / "a").exists()
    assert not part.exists()


def test_resumable_download_with_range(tmp_path, monkeypatch):
    data = b"abcdef"
    artifact = Artifact("a", "https://unused", len(data), hashlib.sha256(data).hexdigest(), "MIT")
    (tmp_path / "a.part").write_bytes(data[:3])

    def handler(request):
        assert request.headers["Range"] == "bytes=3-"
        return httpx.Response(206, headers={"Content-Range": "bytes 3-5/6"}, content=data[3:])

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    ModelManager.download(artifact, tmp_path / "a")
    assert (tmp_path / "a").read_bytes() == data
