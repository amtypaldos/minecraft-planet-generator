# Planet Generator — Bedrock Server Packs

Custom scripting add-on for a Minecraft Bedrock Dedicated Server. See the [root README](../README.md) for full setup and install instructions.

---

## Managing planets

### TUI (recommended)

```bash
cd packs
uv run tui.py
```

The TUI shows all planets in a table. Keys:

| Key | Action |
|-----|--------|
| `a` | Add new planet |
| `e` | Edit selected planet |
| `d` | Delete selected planet |
| `q` | Quit |

After any change, restart the server: `docker compose restart` (from the repo root).

### CLI

```bash
# Add
uv run add_planet.py "Haumea" --radius 3 --block white_wool
uv run add_planet.py "Nibiru" --radius 20 --block purple_concrete --ring-block cyan_wool
uv run add_planet.py "Eris"   --radius 4  --block white_wool --color c8d8ff

# Edit
uv run add_planet.py "Earth"  --edit --block blue_concrete
uv run add_planet.py "Saturn" --edit --ring-block white_concrete

# Delete
uv run add_planet.py "Haumea" --delete

# List
uv run add_planet.py --list
```

Both TUI and CLI bump the RP version automatically so clients re-download updated textures on next connect.

---

## Planet items

Ten planet items (Sun through Pluto) appear in the creative inventory under the **Items** tab. Search by name or give directly:

```
/give @s space:sun
/give @s space:earth
/give @s space:saturn
```

**Using an item:** hold it and right-click in the air while looking toward where you want the planet. Spawns immediately in front of you.

---

## `/space:planet` command

```
/space:planet <radius> <block>
/space:planet 30 glowstone
/space:planet 8 light_blue_wool
/space:planet 50 blue_ice
```

Generates a hollow sphere (2-block shell) centered in front of the player. Radius 1–150.

---

## Restoring the world

Stop the server, swap the world directory, re-enable Beta APIs, then start again:

```bash
docker compose stop
rm -rf "../data/worlds/${LEVEL_NAME:-Minecraft}"
cp -r "../data/worlds/${LEVEL_NAME:-Minecraft}.bak-TIMESTAMP" "../data/worlds/${LEVEL_NAME:-Minecraft}"
uv run main.py "../data/worlds/${LEVEL_NAME:-Minecraft}/level.dat"
docker compose start
```

---

## How the pack loads

Source files live in `packs/` (git-tracked). Docker mounts them directly — no copying needed. Changes take effect after `docker compose restart`.

```
packs/
├── planet_generator/          → /data/behavior_packs/planet_generator
├── planet_generator_rp/       → /data/development_resource_packs/planet_generator_rp
├── world_behavior_packs.json  → /data/worlds/<LEVEL_NAME>/world_behavior_packs.json
└── world_resource_packs.json  → /data/worlds/<LEVEL_NAME>/world_resource_packs.json
```

`texturepack-required=true` is set in `docker-compose.yaml` so clients are prompted to download the resource pack on first connect.

---

## Python tooling

Dependencies are managed with [uv](https://docs.astral.sh/uv/getting-started/installation/) in `packs/pyproject.toml`.

```bash
cd packs
uv sync          # install / update dependencies
uv run <script>  # run any script in the venv
```

| Script | Purpose |
|--------|---------|
| `tui.py` | Interactive planet manager (TUI) |
| `add_planet.py` | CLI planet manager / importable library |
| `gen_planet_textures.py` | Regenerate all original planet icons |
| `main.py <level.dat>` | Enable Beta APIs experiment in a world's level.dat |
| `build.py` | Build `planet-generator-x.x.x.mcaddon` for local install |
| `version.py <major\|minor\|patch\|x.y.z>` | Bump version, commit, and tag for release |

---

## Pack structure

```
planet_generator/
├── manifest.json          — pack identity, @minecraft/server + server-ui deps, RP dependency
├── items/                 — one JSON per planet item (space:sun … space:pluto)
└── scripts/
    └── main.js            — sphere + ring generation, item use handler, /space:planet command

planet_generator_rp/
├── manifest.json          — resource pack identity
└── textures/
    ├── item_texture.json  — maps space_* keys to PNG paths
    └── items/             — 32×32 RGBA planet sphere icons (Pillow-generated)
```

### Key facts

- `@minecraft/server` **2.6.0** — latest stable on BDS 1.26.x
- `@minecraft/server-ui` **2.0.0** — for `ModalFormData` item-use forms
- **Beta APIs** experiment must be enabled in `level.dat` for `/space:planet` and custom items to work
- `system.beforeEvents.startup` is the correct hook for `customCommandRegistry` in 2.6.0
- `world.afterEvents.itemUse` handles item right-clicks (`itemUseOn` is undefined in 2.6.0)
- RP version is bumped automatically after every planet change — clients re-download on next connect
