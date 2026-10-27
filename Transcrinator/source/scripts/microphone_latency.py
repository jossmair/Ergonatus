"""Compare capture latency using numeric diagnostics only, never save audio."""
import json
import time
from pathlib import Path

from app.core.audio_capture import AudioCapture


def main():
    results = []
    for latency in ("high", "low"):
        capture = AudioCapture(latency=latency)
        started = time.monotonic()
        try:
            capture.start()
            opened = time.monotonic()
            first = None
            blocks = 0
            samples = 0
            deadline = opened + 3
            while time.monotonic() < deadline:
                block = capture.read()
                if block:
                    audio, _ = block
                    if first is None:
                        first = time.monotonic()
                    samples += len(audio)
                    blocks += 1
                time.sleep(0.005)
            results.append({
                "requested_latency": latency,
                "driver_latency_ms": round(capture.stream.latency * 1000, 1),
                "opening_ms": round((opened - started) * 1000, 1),
                "first_block_after_open_ms": round((first - opened) * 1000, 1) if first else None,
                "blocks_in_3_seconds": blocks,
                "resampled_samples": samples,
                "overflow": capture.failed.is_set(),
            })
        finally:
            capture.stop()
    path = Path("docs/validation/microphone-latency-111.json")
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results))
    assert all(r["blocks_in_3_seconds"] > 30 and not r["overflow"] for r in results)


if __name__ == "__main__":
    main()
