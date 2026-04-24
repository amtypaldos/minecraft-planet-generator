"""
Bump the pack version, commit, and tag for release.

Usage:
    uv run version.py patch        # 1.1.22 → 1.1.23
    uv run version.py minor        # 1.1.22 → 1.2.0
    uv run version.py major        # 1.1.22 → 2.0.0
    uv run version.py 1.2.0        # set explicitly
"""
import json
import subprocess
import sys
from pathlib import Path

PACKS = Path(__file__).parent
BP_MANIFEST = PACKS / "planet_generator" / "manifest.json"
RP_MANIFEST = PACKS / "planet_generator_rp" / "manifest.json"
WORLD_BP_JSON = PACKS / "world_behavior_packs.json"
WORLD_RP_JSON = PACKS / "world_resource_packs.json"


def read_version(path: Path) -> list[int]:
    return json.loads(path.read_text())["header"]["version"]


def write_version(path: Path, version: list[int]) -> None:
    data = json.loads(path.read_text())
    data["header"]["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]
    current = read_version(RP_MANIFEST)
    major, minor, patch = current

    if arg == "major":
        new = [major + 1, 0, 0]
    elif arg == "minor":
        new = [major, minor + 1, 0]
    elif arg == "patch":
        new = [major, minor, patch + 1]
    else:
        parts = arg.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            print(f"ERROR: version must be major/minor/patch or X.Y.Z, got '{arg}'")
            sys.exit(1)
        new = [int(p) for p in parts]

    old_str = ".".join(str(v) for v in current)
    new_str = ".".join(str(v) for v in new)

    # check for uncommitted changes (excluding manifests we're about to edit)
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=PACKS.parent,
    )
    dirty = [
        l for l in result.stdout.splitlines()
        if not any(m in l for m in ["manifest.json", "world_resource_packs.json"])
    ]
    if dirty:
        print("ERROR: uncommitted changes — commit or stash before versioning:")
        print("\n".join(f"  {l}" for l in dirty))
        sys.exit(1)

    print(f"Bumping version: {old_str} → {new_str}")

    write_version(BP_MANIFEST, new)
    write_version(RP_MANIFEST, new)

    # keep world pack JSON files in sync
    world_bp = json.loads(WORLD_BP_JSON.read_text())
    world_bp[0]["version"] = new
    WORLD_BP_JSON.write_text(json.dumps(world_bp, indent=2) + "\n")

    world_rp = json.loads(WORLD_RP_JSON.read_text())
    world_rp[0]["version"] = new
    WORLD_RP_JSON.write_text(json.dumps(world_rp) + "\n")

    tag = f"v{new_str}"
    run(["git", "-C", str(PACKS.parent), "add",
         str(BP_MANIFEST), str(RP_MANIFEST), str(WORLD_BP_JSON), str(WORLD_RP_JSON)])
    run(["git", "-C", str(PACKS.parent), "commit", "-m", f"Release {tag}"])
    run(["git", "-C", str(PACKS.parent), "tag", tag])

    print(f"✓ Committed and tagged {tag}")
    print(f"  Push with: git push origin main {tag}")


if __name__ == "__main__":
    main()
