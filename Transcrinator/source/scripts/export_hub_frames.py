"""Export generated production atlases as aligned, small transparent PNG resources."""
import json
from pathlib import Path

from PIL import Image


def main():
    root = Path("assets/hud-orange")
    output = root / "frames"
    output.mkdir(exist_ok=True)
    exports = []
    for family, span in (("core", 192), ("orbit", 210), ("flare", 224)):
        path = root / "atlases" / f"{family}-loop-v1.png"
        with Image.open(path) as original:
            atlas = original.convert("RGBA")
        width, height = atlas.width // 2, atlas.height // 2
        for index in range(4):
            x, y = (index % 2) * width, (index // 2) * height
            cell = atlas.crop((x, y, x + width, y + height))
            bounds = cell.getchannel("A").point(lambda alpha: 255 if alpha >= 128 else 0).getbbox()
            if not bounds:
                raise RuntimeError(f"Empty animation cell: {family} {index}")
            left, top, right, bottom = bounds
            scale = span / max(right - left, bottom - top)
            resized = cell.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
            origin = (round(128 - (left + right) / 2 * scale),
                      round(128 - (top + bottom) / 2 * scale))
            frame = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            frame.paste(resized, origin)
            target = output / f"{family}-{index:02}.png"
            frame.save(target, optimize=True)
            exports.append({"file": target.as_posix(), "atlas": path.as_posix(),
                            "source_cell": [x, y, width, height], "alignment_bounds": bounds,
                            "scale": scale, "origin": origin, "size": [256, 256],
                            "bytes": target.stat().st_size})
    (root / "atlases/frame-export.json").write_text(
        json.dumps({"operation": "cell extraction, recentering and size normalization only",
                    "artwork_generator": "built-in image_gen", "exports": exports}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"png_frames": len(exports), "bytes": sum(row["bytes"] for row in exports)}))


if __name__ == "__main__":
    main()
