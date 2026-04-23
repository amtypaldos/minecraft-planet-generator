#!/usr/bin/env bash
# First-time install for the Planet Generator Bedrock server.
# Run once after cloning the repo on a new machine.
#
# Prerequisites:
#   - Docker + Docker Compose installed and running
#   - uv installed (https://docs.astral.sh/uv/getting-started/installation/)
#   - (Optional) mc-macvlan Docker network for a dedicated LAN IP:
#       docker network create -d macvlan \
#         --subnet=192.168.X.0/24 --gateway=192.168.X.1 \
#         -o parent=eth0 mc-macvlan
#     If you skip this, set networks: [default] in docker-compose.yaml instead.
#
# Configuration (optional — create a .env file to override):
#   LEVEL_NAME=My Solar System   # world/save name (default: Minecraft)
#   SERVER_IP=192.168.1.50       # IP for macvlan network

set -euo pipefail
cd "$(dirname "$0")"

LEVEL_NAME="${LEVEL_NAME:-Minecraft}"
LEVEL_DAT="data/worlds/$LEVEL_NAME/level.dat"

echo "=== Planet Generator — install ==="
echo ""

# ── prerequisites ─────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker not found. Install Docker first." && exit 1
fi
if ! docker info &>/dev/null; then
  echo "ERROR: Docker daemon not running." && exit 1
fi
if ! command -v uv &>/dev/null && ! ~/.local/bin/uv version &>/dev/null; then
  echo "ERROR: uv not found. Install from https://docs.astral.sh/uv/getting-started/installation/" && exit 1
fi
UV=$(command -v uv 2>/dev/null || echo ~/.local/bin/uv)

if ! docker network inspect mc-macvlan &>/dev/null; then
  echo "WARNING: mc-macvlan network not found."
  echo "  Create it first — see the Prerequisites comment at the top of this script."
  echo "  Continuing anyway (server will fail to start without it)."
  echo ""
fi

# ── python tooling ────────────────────────────────────────────────────────────
echo "Setting up Python tooling..."
(cd packs && "$UV" sync --quiet)
echo "✓ uv dependencies installed"
echo ""

# ── first boot ────────────────────────────────────────────────────────────────
echo "Starting server for the first time (downloads image + generates world)..."
docker compose up -d

echo "Waiting for world to generate..."
until docker logs bedrock-planets 2>&1 | grep -q "Server started"; do
  sleep 3
done
echo "✓ World generated"
echo ""

# ── enable beta apis ──────────────────────────────────────────────────────────
echo "Stopping server to patch level.dat..."
docker compose stop

echo "Enabling Beta APIs experiment (required for /space:planet command)..."
"$UV" run packs/main.py "$LEVEL_DAT"
echo ""

# ── start for real ───────────────────────────────────────────────────────────
echo "Starting server..."
docker compose start

echo "Waiting for server to be ready..."
until docker logs bedrock-planets 2>&1 | grep -q "Server started"; do
  sleep 2
done

echo ""
echo "=== Done! ==="
echo ""
echo "Server is running at $(docker inspect bedrock-planets | python3 -c "import sys,json; nets=json.load(sys.stdin)[0]['NetworkSettings']['Networks']; print(list(nets.values())[0].get('IPAMConfig',{}).get('IPv4Address','(see docker-compose.yaml)'))" 2>/dev/null || echo "(see docker-compose.yaml)")"
echo ""
echo "Next steps:"
echo "  - Connect in Bedrock and accept the resource pack download"
echo "  - Grab planet items from creative inventory (search by name)"
echo "  - Or use: /space:planet <radius> <block>"
echo ""
echo "To manage planets (TUI):"
echo "  cd packs && uv run tui.py"
