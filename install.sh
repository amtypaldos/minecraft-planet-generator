#!/usr/bin/env bash
# Planet Generator — install script
#
# Modes:
#   bash install.sh                          # Docker Compose (new BDS server)
#   bash install.sh --server-dir /path/bds   # Existing BDS server data directory
#
# Configuration (env vars or .env file):
#   LEVEL_NAME=Minecraft        world/save folder name (default: Minecraft)
#   SERVER_IP=192.168.1.50      IP for macvlan Docker network (Docker mode only)
#
# Docker mode prerequisites:
#   - Docker + Docker Compose
#   - uv  (https://docs.astral.sh/uv/getting-started/installation/)
#   - Optional: mc-macvlan Docker network for a dedicated LAN IP
#       docker network create -d macvlan \
#         --subnet=192.168.X.0/24 --gateway=192.168.X.1 \
#         -o parent=eth0 mc-macvlan
#
# Existing server mode prerequisites:
#   - A running Minecraft Bedrock Dedicated Server (1.21+)
#   - uv  (https://docs.astral.sh/uv/getting-started/installation/)

set -euo pipefail
cd "$(dirname "$0")"

# ── parse args ────────────────────────────────────────────────────────────────
SERVER_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --server-dir=*) SERVER_DIR="${1#*=}"; shift ;;
    *) echo "Unknown argument: $1" && exit 1 ;;
  esac
done

LEVEL_NAME="${LEVEL_NAME:-Minecraft}"
UV=$(command -v uv 2>/dev/null || echo ~/.local/bin/uv)

echo "=== Planet Generator — install ==="
echo ""

# ── check uv ─────────────────────────────────────────────────────────────────
if ! "$UV" version &>/dev/null; then
  echo "ERROR: uv not found. Install from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

echo "Setting up Python tooling..."
(cd packs && "$UV" sync --quiet)
echo "✓ uv dependencies installed"
echo ""

# ── helper: merge pack entry into a world JSON file ───────────────────────────
merge_pack_json() {
  local file="$1" pack_id="$2" version="$3"
  if [[ ! -f "$file" ]]; then
    echo "[]" > "$file"
  fi
  "$UV" run python3 - "$file" "$pack_id" "$version" <<'PYEOF'
import json, sys
path, pack_id, ver_str = sys.argv[1], sys.argv[2], sys.argv[3]
version = [int(x) for x in ver_str.split(".")]
packs = json.loads(open(path).read()) or []
if not any(p.get("pack_id") == pack_id for p in packs):
    packs.append({"pack_id": pack_id, "version": version})
    open(path, "w").write(json.dumps(packs, indent=2))
    print(f"  Added {pack_id} to {path}")
else:
    print(f"  {pack_id} already present in {path}")
PYEOF
}

# ══════════════════════════════════════════════════════════════════════════════
if [[ -n "$SERVER_DIR" ]]; then
# ── existing server mode ──────────────────────────────────────────────────────

  if [[ ! -d "$SERVER_DIR" ]]; then
    echo "ERROR: --server-dir '$SERVER_DIR' does not exist." && exit 1
  fi

  LEVEL_DAT="$SERVER_DIR/worlds/$LEVEL_NAME/level.dat"
  if [[ ! -f "$LEVEL_DAT" ]]; then
    echo "ERROR: level.dat not found at $LEVEL_DAT"
    echo "  Check that LEVEL_NAME='$LEVEL_NAME' matches your world folder name."
    exit 1
  fi

  echo "Mode: existing BDS server at $SERVER_DIR"
  echo "World: $LEVEL_NAME"
  echo ""

  # copy behavior pack
  echo "Copying behavior pack..."
  rm -rf "$SERVER_DIR/behavior_packs/planet_generator"
  cp -r packs/planet_generator "$SERVER_DIR/behavior_packs/planet_generator"
  echo "✓ planet_generator → $SERVER_DIR/behavior_packs/"

  # copy resource pack
  echo "Copying resource pack..."
  rm -rf "$SERVER_DIR/resource_packs/planet_generator_rp"
  cp -r packs/planet_generator_rp "$SERVER_DIR/resource_packs/planet_generator_rp"
  echo "✓ planet_generator_rp → $SERVER_DIR/resource_packs/"
  echo ""

  # merge world pack lists (read UUIDs + versions from manifests, not hardcoded)
  echo "Enabling packs in world..."
  WORLD_DIR="$SERVER_DIR/worlds/$LEVEL_NAME"
  BP_UUID=$("$UV" run python3 -c "import json; m=json.load(open('packs/planet_generator/manifest.json')); print(m['header']['uuid'])")
  BP_VER=$("$UV" run python3 -c "import json; m=json.load(open('packs/planet_generator/manifest.json')); print('.'.join(str(v) for v in m['header']['version']))")
  RP_UUID=$("$UV" run python3 -c "import json; m=json.load(open('packs/planet_generator_rp/manifest.json')); print(m['header']['uuid'])")
  RP_VER=$("$UV" run python3 -c "import json; m=json.load(open('packs/planet_generator_rp/manifest.json')); print('.'.join(str(v) for v in m['header']['version']))")
  merge_pack_json "$WORLD_DIR/world_behavior_packs.json" "$BP_UUID" "$BP_VER"
  merge_pack_json "$WORLD_DIR/world_resource_packs.json" "$RP_UUID" "$RP_VER"
  echo ""

  # patch level.dat
  echo "Enabling Beta APIs experiment..."
  "$UV" run packs/main.py "$LEVEL_DAT"
  echo ""

  echo "=== Done! ==="
  echo ""
  echo "Restart your Bedrock server for the changes to take effect."
  echo ""
  echo "In-game:"
  echo "  - Planet items appear in creative inventory (search by name)"
  echo "  - Or use: /space:planet <radius> <block>"
  echo ""
  echo "To manage planets (TUI):"
  echo "  cd packs && uv run tui.py"

else
# ── docker compose mode ───────────────────────────────────────────────────────

  if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker not found. Install Docker first." && exit 1
  fi
  if ! docker info &>/dev/null; then
    echo "ERROR: Docker daemon not running." && exit 1
  fi
  if ! docker network inspect mc-macvlan &>/dev/null; then
    echo "WARNING: mc-macvlan network not found."
    echo "  Create it first — see Prerequisites at the top of this script."
    echo "  Continuing anyway (server will fail to start without it)."
    echo ""
  fi

  LEVEL_DAT="data/worlds/$LEVEL_NAME/level.dat"

  echo "Mode: Docker Compose (new BDS server)"
  echo ""

  echo "Starting server for the first time (downloads image + generates world)..."
  docker compose up -d

  echo "Waiting for world to generate..."
  until docker logs bedrock-planets 2>&1 | grep -q "Server started"; do
    sleep 3
  done
  echo "✓ World generated"
  echo ""

  echo "Stopping server to patch level.dat..."
  docker compose stop

  echo "Enabling Beta APIs experiment..."
  "$UV" run packs/main.py "$LEVEL_DAT"
  echo ""

  echo "Starting server..."
  docker compose start

  echo "Waiting for server to be ready..."
  until docker logs bedrock-planets 2>&1 | grep -q "Server started"; do
    sleep 2
  done

  echo ""
  echo "=== Done! ==="
  echo ""
  echo "Server is running at $(docker inspect bedrock-planets | python3 -c "
import sys, json
nets = json.load(sys.stdin)[0]['NetworkSettings']['Networks']
cfg = list(nets.values())[0].get('IPAMConfig') or {}
print(cfg.get('IPv4Address', '(see docker-compose.yaml)'))
" 2>/dev/null || echo "(see docker-compose.yaml)")"
  echo ""
  echo "Next steps:"
  echo "  - Connect in Bedrock and accept the resource pack download"
  echo "  - Grab planet items from creative inventory (search by name)"
  echo "  - Or use: /space:planet <radius> <block>"
  echo ""
  echo "To manage planets (TUI):"
  echo "  cd packs && uv run tui.py"

fi
