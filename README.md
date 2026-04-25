# Planet Generator — Minecraft Bedrock Add-on

A Bedrock Dedicated Server add-on that lets you place hollow planet spheres in-game. Each planet is a creative-inventory item — hold it, right-click, and a sphere generates in front of you. Comes with Sun through Pluto pre-built, and a TUI for adding your own.

```
┌─ Planet Generator ──────────────────── Bedrock add-on manager ─┐
│                                                                  │
│  Name      ID               Radius  Block            Rings      │
│  ────────  ───────────────  ──────  ───────────────  ────────   │
│  Sun       space:sun        30      glowstone         —         │
│  Mercury   space:mercury    4       gravel            —         │
│▶ Earth     space:earth      8       light_blue_wool   —         │
│  Mars      space:mars       6       red_sandstone     —         │
│  Jupiter   space:jupiter    18      orange_wool       —         │
│  Saturn    space:saturn     14      yellow_wool       white_..  │
│  ...                                                             │
│                                                                  │
│  [a] Add  [e] Edit  [d] Delete  [q] Quit                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Local install (mobile / Windows)

No server needed. Download the `.mcaddon` from the [GitHub Releases page](../../releases) and open it directly in Minecraft.

**Step 1 — Import the packs**

- **Windows:** double-click the `.mcaddon` file — Minecraft opens and imports both packs automatically
- **Mobile:** tap the `.mcaddon` file and choose **Open with Minecraft** (or share → Minecraft)

**Step 2 — Create a new world with Beta APIs enabled**

> **Important:** Beta APIs must be enabled at world creation — it cannot be toggled on an existing world, especially on mobile.

1. In Minecraft, tap **Create New World**
2. Go to **Experiments** → enable **Beta APIs**
3. Go to **Resource Packs** → activate Planet Generator RP
4. Go to **Behavior Packs** → activate Planet Generator BP
5. Create the world — planet items appear in the creative inventory under the Items tab

On mobile, long-press while holding a planet item to spawn it.

---

## Self-hosted server

Two install modes — pick the one that fits your setup.

### Option A: Docker (new server)

Spins up a fresh Bedrock Dedicated Server in Docker.

**Prerequisites:** Docker + Compose, uv

```bash
git clone <repo-url>
cd minecraft
bash install.sh
```

`install.sh` will:
1. Install Python dependencies via `uv`
2. Start the server (downloads the Bedrock image on first run)
3. Wait for the world to generate
4. Patch `level.dat` to enable Beta APIs
5. Restart the server

Connect in Bedrock, accept the resource pack download, and you're in.

#### Docker configuration

Create a `.env` file to override defaults:

```dotenv
LEVEL_NAME=My Solar System   # world/save folder name (default: Minecraft)
SERVER_IP=192.168.1.50       # IP for macvlan network
```

The default config uses a **macvlan** network so the server gets its own LAN IP. If you don't need this, edit `docker-compose.yaml` and replace the networks block with `networks: [default]`.

To create the macvlan network:
```bash
docker network create -d macvlan \
  --subnet=192.168.X.0/24 \
  --gateway=192.168.X.1 \
  -o parent=eth0 \
  mc-macvlan
```
Replace `192.168.X.x` with your LAN subnet and `eth0` with your interface (`ip link` to check).

---

### Option B: Existing BDS

Adds the packs to a Bedrock Dedicated Server you already have running.

**Prerequisites:** uv

```bash
git clone <repo-url>
cd minecraft
bash install.sh --server-dir /path/to/your/bedrock-server
```

`install.sh` will:
1. Copy both packs into `behavior_packs/` and `resource_packs/`
2. Register the packs in your world's pack JSON files (non-destructive — existing packs are preserved)
3. Patch `level.dat` to enable Beta APIs

Then restart your BDS. Set `LEVEL_NAME` if your world folder isn't named `Minecraft`:

```bash
LEVEL_NAME="My World" bash install.sh --server-dir /path/to/bedrock-server
```

---

## Managing planets

```bash
cd packs
uv run tui.py        # interactive TUI (recommended)
uv run add_planet.py --list   # list planets in terminal
```

The TUI lets you add, edit, and delete planets with forms. After any change, restart the server:

```bash
docker compose restart
```

### CLI (for scripting)

```bash
uv run add_planet.py "Haumea" --radius 3 --block white_wool
uv run add_planet.py "Earth"  --edit --block blue_concrete
uv run add_planet.py "Haumea" --delete
```

---

## In-game usage

**Planet items** appear in the creative inventory under the **Items** tab. Search by name or give them directly:

```
/give @s space:earth
/give @s space:saturn
```

Hold a planet item and **right-click** to spawn it in front of you.

**Command** (for operators):
```
/space:planet <radius> <block>
/space:planet 30 glowstone
/space:planet 50 blue_ice
```

---

## World restore

```bash
docker compose stop
rm -rf "data/worlds/${LEVEL_NAME:-Minecraft}"
cp -r "data/worlds/${LEVEL_NAME:-Minecraft}.bak-TIMESTAMP" "data/worlds/${LEVEL_NAME:-Minecraft}"
uv run packs/main.py "data/worlds/${LEVEL_NAME:-Minecraft}/level.dat"
docker compose start
```

The Beta APIs experiment flag doesn't survive a world restore — `main.py` re-enables it.

---

## Pack structure

```
packs/
├── planet_generator/           → behavior pack (scripts + item definitions)
│   ├── manifest.json
│   ├── scripts/main.js         — sphere/ring generation, item use handler
│   └── items/space_*.json      — one JSON per planet item
├── planet_generator_rp/        → resource pack (textures)
│   ├── manifest.json
│   └── textures/
│       ├── item_texture.json
│       └── items/space_*.png   — 32×32 planet icons (Pillow-generated)
├── tui.py                      — interactive planet manager (Textual)
├── add_planet.py               — CLI planet manager / library
├── gen_planet_textures.py      — regenerate all original planet icons
├── main.py                     — enable Beta APIs in level.dat
└── pyproject.toml              — Python deps (nbtlib, Pillow, textual)
```

### Technical notes

- Bedrock server: `itzg/minecraft-bedrock-server:latest`
- `@minecraft/server` **2.6.0**, `@minecraft/server-ui` **2.0.0**
- **Beta APIs** experiment must be enabled in `level.dat` — `install.sh` does this automatically; re-run `main.py` after any world restore
- Sphere generation uses `system.runJob()` to spread block placement across ticks — no server freeze
- RP version is bumped automatically after every planet change so clients re-download updated textures

---

## License

MIT — see [LICENSE](LICENSE).
