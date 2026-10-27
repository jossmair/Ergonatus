"""Render the original vector identity for Windows; development tool only."""
from pathlib import Path
import io
import cairosvg
from PIL import Image

root = Path(__file__).resolve().parents[1]
png = cairosvg.svg2png(url=str(root / 'assets/ecrinator.svg'), output_width=256, output_height=256)
(root / 'assets/ecrinator.png').write_bytes(png)
with Image.open(io.BytesIO(png)) as icon:
    icon.save(root / 'assets/ecrinator.ico', sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
print('Windows identity rendered from assets/ecrinator.svg')
