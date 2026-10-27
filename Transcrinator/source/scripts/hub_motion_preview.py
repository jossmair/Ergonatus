"""Render the native hub driven by the synthetic French test corpus, not a live recording."""
import io
import wave
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication

from app.core.settings import Settings
from app.ui.floating_hub import FloatingHub


def main():
    application = QApplication.instance() or QApplication([])
    with wave.open("vendor/corpus/fr03.wav", "rb") as stream:
        rate = stream.getframerate()
        audio = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32)
        audio = audio.reshape(-1, stream.getnchannels()).mean(axis=1) / 32768
    hub = FloatingHub(Settings())
    hub.set_state("Écoute…")
    hub.finish_transition()
    hub.timer.stop()
    frames = []
    for offset in range(0, len(audio), rate // 30):
        chunk = audio[offset:offset + rate // 30]
        hub.set_level(float(np.sqrt(np.mean(chunk * chunk))))
        hub.animate()
        hub.animate()
        application.processEvents()
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        hub.grab().save(buffer, "PNG")
        frame = Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB")
        frames.append(frame)
    output = Path("docs/validation/hub-motion-preview.gif")
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=33, loop=0)
    hub.hide()
    print(output)


if __name__ == "__main__":
    main()
