"""Build planet-generator.mcaddon for local Minecraft installation."""
import json
import zipfile
from pathlib import Path

PACK_DIR = Path(__file__).parent
RP_MANIFEST = PACK_DIR / "planet_generator_rp" / "manifest.json"

version = json.loads(RP_MANIFEST.read_text())["header"]["version"]
ver_str = ".".join(str(v) for v in version)
output = PACK_DIR.parent / f"planet-generator-{ver_str}.mcaddon"

with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
    for pack in ["planet_generator", "planet_generator_rp"]:
        for f in (PACK_DIR / pack).rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(PACK_DIR))

print(f"Built: {output.name}")
