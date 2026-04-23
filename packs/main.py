"""
enable_beta_apis.py

Enables the Beta APIs experiment in a Bedrock world's level.dat.
This unlocks system.registerCommand() in the scripting API, allowing
true custom slash commands with autocomplete (e.g. /planet).

Usage:
    uv run main.py <path-to-level.dat>

Bedrock level.dat format:
    - 4 bytes: storage version (little-endian int32)
    - 4 bytes: NBT data length (little-endian int32)
    - N bytes: little-endian NBT data
"""

import sys
import struct
import shutil
import io
from datetime import datetime
from pathlib import Path

import nbtlib


def load_bedrock_level_dat(path: Path):
    data = path.read_bytes()
    header = data[:8]
    nbt_data = data[8:]
    version, length = struct.unpack("<II", header)
    nbt = nbtlib.File.parse(io.BytesIO(nbt_data), byteorder="little")
    return version, nbt


def save_bedrock_level_dat(path: Path, version: int, nbt):
    buf = io.BytesIO()
    nbt.write(buf, byteorder="little")
    nbt_bytes = buf.getvalue()
    header = struct.pack("<II", version, len(nbt_bytes))
    path.write_bytes(header + nbt_bytes)



def enable_beta_apis(level_dat_path: Path):
    backup_path = level_dat_path.with_suffix(
        f".dat.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    shutil.copy2(level_dat_path, backup_path)
    print(f"Backed up to {backup_path.name}")

    version, nbt = load_bedrock_level_dat(level_dat_path)

    if "experiments" not in nbt:
        nbt["experiments"] = nbtlib.Compound()

    nbt["experiments"]["beta_apis"] = nbtlib.Byte(1)
    nbt["experiments"]["experiments_ever_used"] = nbtlib.Byte(1)
    nbt["experiments"]["saved_with_toggled_experiments"] = nbtlib.Byte(1)

    save_bedrock_level_dat(level_dat_path, version, nbt)
    print("Beta APIs experiment enabled.")
    print("Restart the server — /planet should now work with autocomplete.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: uv run main.py <path-to-level.dat>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: {path} not found")
        sys.exit(1)

    enable_beta_apis(path)
