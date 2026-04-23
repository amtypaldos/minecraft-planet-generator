"""
Add or edit a planet in the Planet Generator pack (CLI interface).

For the interactive TUI run:
    uv run tui.py

CLI usage:
    uv run add_planet.py "Haumea" --radius 3 --block white_wool
    uv run add_planet.py "Nibiru" --radius 20 --block purple_concrete --ring-block cyan_wool
    uv run add_planet.py "Eris"  --radius 4  --block white_wool --color c8d8ff
    uv run add_planet.py "Earth" --edit --block blue_concrete
    uv run add_planet.py "Saturn" --edit --block yellow_concrete --ring-block white_concrete
    uv run add_planet.py "Haumea" --delete
    uv run add_planet.py --list

After running, restart the server:
    docker compose restart
"""

import argparse, json, math, random, re, sys
from pathlib import Path

PACK_DIR      = Path(__file__).parent
BP_DIR        = PACK_DIR / "planet_generator"
RP_DIR        = PACK_DIR / "planet_generator_rp"
ITEMS_DIR     = BP_DIR   / "items"
TEXTURES_DIR  = RP_DIR   / "textures" / "items"
MAIN_JS       = BP_DIR   / "scripts"  / "main.js"
TEXTURE_JSON  = RP_DIR   / "textures" / "item_texture.json"
RP_MANIFEST   = RP_DIR   / "manifest.json"
WORLD_RP_JSON = PACK_DIR / "world_resource_packs.json"

# Approximate colors for common block names
BLOCK_COLORS = {
    "air": (200, 200, 255), "stone": (130, 130, 130), "gravel": (150, 140, 135),
    "sand": (225, 210, 150), "sandstone": (230, 200, 120),
    "red_sandstone": (190, 80, 40), "netherrack": (160, 60, 60),
    "glowstone": (255, 210, 30), "obsidian": (30, 20, 50),
    "dirt": (140, 100, 60), "grass": (90, 160, 60), "grass_block": (90, 160, 60),
    "snow": (240, 245, 255), "ice": (160, 200, 240), "blue_ice": (100, 160, 240),
    "white_wool": (240, 240, 240), "orange_wool": (215, 120, 40),
    "magenta_wool": (190, 75, 185), "light_blue_wool": (100, 175, 220),
    "yellow_wool": (225, 200, 45), "lime_wool": (100, 200, 60),
    "pink_wool": (235, 140, 170), "gray_wool": (90, 90, 95),
    "light_gray_wool": (160, 160, 165), "cyan_wool": (45, 155, 165),
    "purple_wool": (130, 55, 180), "blue_wool": (40, 80, 200),
    "brown_wool": (110, 70, 35), "green_wool": (60, 100, 35),
    "red_wool": (165, 40, 40), "black_wool": (25, 25, 28),
    "white_concrete": (210, 215, 215), "orange_concrete": (230, 100, 25),
    "magenta_concrete": (180, 60, 175), "light_blue_concrete": (55, 155, 205),
    "yellow_concrete": (245, 180, 20), "lime_concrete": (95, 170, 25),
    "pink_concrete": (220, 100, 140), "gray_concrete": (60, 65, 70),
    "light_gray_concrete": (130, 135, 135), "cyan_concrete": (20, 130, 145),
    "purple_concrete": (105, 35, 160), "blue_concrete": (40, 55, 155),
    "brown_concrete": (100, 65, 35), "green_concrete": (75, 95, 20),
    "red_concrete": (145, 30, 25), "black_concrete": (10, 10, 15),
    "quartz_block": (235, 228, 220), "calcite": (225, 225, 220),
    "amethyst_block": (150, 100, 200), "copper_block": (190, 120, 75),
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def parse_hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def color_for_block(block: str) -> tuple[int, int, int]:
    block = block.lower()
    for key, color in BLOCK_COLORS.items():
        if key in block:
            return color
    return (150, 150, 160)


def lerp(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def generate_icon(item_key: str, base: tuple, ring_block: str | None) -> Path:
    from PIL import Image, ImageDraw, ImageFilter

    SIZE = 32
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    cx, cy = SIZE / 2, SIZE / 2
    r_max = SIZE / 2 - 1
    has_rings = ring_block is not None
    pr = r_max * 0.72 if has_rings else r_max

    shadow    = tuple(max(0, int(c * 0.45)) for c in base)
    highlight = tuple(min(255, int(c * 1.4 + 30)) for c in base)

    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    rng = random.Random(item_key)

    for bx in range(SIZE):
        for by in range(SIZE):
            dx, dy = bx - cx, by - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > pr:
                continue

            shade = 1.0 - 0.5 * (dx * 0.6 + dy * 0.3) / pr
            shade = max(0.3, min(1.2, shade))
            pixel = lerp(shadow, base, min(1.0, shade))

            lat = dy / pr
            wave = math.sin(lat * math.pi * (3 + rng.random()) + rng.random() * 2)
            if wave > 0.2:
                darker = tuple(max(0, c - 25) for c in pixel)
                pixel = lerp(pixel, darker, (wave - 0.2) / 0.8 * 0.4)

            limb = max(0.0, 1.0 - dist / pr)
            if limb < 0.15:
                pixel = lerp(highlight, pixel, limb / 0.15)

            sdx = bx - cx * 0.55
            sdy = by - cy * 0.55
            spec = max(0.0, 1.0 - math.sqrt(sdx * sdx + sdy * sdy) / (pr * 0.45)) ** 2
            ld.point((bx, by), (
                min(255, int(pixel[0] + spec * 80)),
                min(255, int(pixel[1] + spec * 80)),
                min(255, int(pixel[2] + spec * 80)),
                255,
            ))

    img.paste(layer, (0, 0), layer)

    if has_rings:
        ring_color = color_for_block(ring_block)
        rl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        rld = ImageDraw.Draw(rl)
        for bx in range(SIZE):
            for by in range(SIZE):
                dx, dy = bx - cx, by - cy
                dist = math.sqrt((dx) ** 2 + (dy / 0.35) ** 2)
                if pr * 1.25 <= dist <= pr * 1.9 and abs(dy) < pr * 0.25:
                    if dy > 0 and math.sqrt(dx * dx + dy * dy) < pr:
                        continue
                    fade = 1.0 - abs(dist - pr * 1.6) / (pr * 0.35)
                    alpha = int(max(0, min(180, fade * 180)))
                    rld.point((bx, by), ring_color + (alpha,))
        img = Image.alpha_composite(img, rl.filter(ImageFilter.GaussianBlur(0.5)))

    out = TEXTURES_DIR / f"{item_key}.png"
    img.save(out)
    return out


def parse_planets() -> list[dict]:
    js = MAIN_JS.read_text()
    start = js.find("const PLANETS")
    end = js.find("\n};", start)
    block = js[start:end]
    planets = []
    for line in block.splitlines():
        m = re.search(r"'(space:[^']+)':\s*\{(.+)\}", line)
        if not m:
            continue
        full_id, body = m.group(1), m.group(2)
        def field(key):
            fm = re.search(rf"{key}:\s*'?([^,'}}]+)'?", body)
            return fm.group(1).strip().strip("'") if fm else ""
        planets.append({
            "id":        full_id,
            "name":      field("name"),
            "radius":    field("radius"),
            "block":     field("block"),
            "ring_block": field("ringBlock"),
        })
    return planets


def list_planets() -> None:
    planets = parse_planets()
    cols = ["Name", "ID", "Radius", "Block", "Rings"]
    rows = [
        [p["name"], p["id"], p["radius"], p["block"], p["ring_block"] or "—"]
        for p in planets
    ]
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(cols)]

    def rule(l, m, r):
        return l + m.join("─" * (w + 2) for w in widths) + r

    def row_str(cells):
        return "│ " + " │ ".join(c.ljust(w) for c, w in zip(cells, widths)) + " │"

    print(rule("┌", "┬", "┐"))
    print(row_str(cols))
    print(rule("├", "┼", "┤"))
    for r in rows:
        print(row_str(r))
    print(rule("└", "┴", "┘"))
    print()


def bump_rp_version() -> str:
    manifest = json.loads(RP_MANIFEST.read_text())
    v = manifest["header"]["version"]
    v[2] += 1
    manifest["header"]["version"] = v
    RP_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    world_rp = json.loads(WORLD_RP_JSON.read_text())
    world_rp[0]["version"] = v
    WORLD_RP_JSON.write_text(json.dumps(world_rp) + "\n")
    return f"{v[0]}.{v[1]}.{v[2]}"


def _resolve_planet(target: str) -> dict:
    """Find a planet by display name or ID slug. Raises ValueError if not found."""
    target_slug = slugify(target)
    for p in parse_planets():
        if p["name"].lower() == target.lower() or p["id"] == f"space:{target_slug}":
            return p
    raise ValueError(f"No planet found matching '{target}'. Run --list to see available planets.")


# ── public API (used by both CLI and TUI) ─────────────────────────────────────

def add_planet(
    name: str,
    radius: int,
    block: str,
    ring_block: str | None = None,
    color: str | None = None,
    planet_id: str | None = None,
) -> str:
    """Add a new planet. Returns full_id. Raises ValueError on conflict."""
    pid      = planet_id or slugify(name)
    full_id  = f"space:{pid}"
    item_key = f"space_{pid}"
    item_file = ITEMS_DIR / f"{item_key}.json"

    existing_ids = {p["id"] for p in parse_planets()}
    if full_id in existing_ids:
        raise ValueError(f"{full_id} already exists — use --edit to update it or --delete to remove it first.")
    if item_file.exists():
        raise ValueError(f"{item_file.name} already exists — delete it first to overwrite.")

    # 1. Item JSON
    item_data = {
        "format_version": "1.21.0",
        "minecraft:item": {
            "description": {
                "identifier": full_id,
                "menu_category": {"category": "items"},
            },
            "components": {
                "minecraft:display_name": {"value": name},
                "minecraft:icon": {"textures": {"default": item_key}},
                "minecraft:max_stack_size": 16,
            },
        },
    }
    item_file.write_text(json.dumps(item_data, indent=2) + "\n")
    print(f"✓ {item_file.relative_to(PACK_DIR)}")

    # 2. PLANETS entry in main.js
    js = MAIN_JS.read_text()
    entry = f"  '{full_id}': {{ radius: {radius}, block: '{block}', name: '{name}'"
    if ring_block:
        entry += f", ringBlock: '{ring_block}'"
    entry += " },"
    insert_at = js.find("\n};", js.find("const PLANETS"))
    if insert_at == -1:
        raise ValueError("Could not find PLANETS constant in main.js")
    MAIN_JS.write_text(js[:insert_at] + "\n" + entry + js[insert_at:])
    print(f"✓ Added {full_id} to main.js")

    # 3. item_texture.json
    tex_data = json.loads(TEXTURE_JSON.read_text())
    tex_data["texture_data"][item_key] = {"textures": f"textures/items/{item_key}"}
    TEXTURE_JSON.write_text(json.dumps(tex_data, indent=2) + "\n")
    print(f"✓ Updated item_texture.json")

    # 4. Icon PNG
    base_color = parse_hex(color) if color else color_for_block(block)
    out = generate_icon(item_key, base_color, ring_block)
    print(f"✓ Generated {out.relative_to(PACK_DIR)}")

    # 5. Bump RP version
    new_ver = bump_rp_version()
    print(f"✓ Bumped RP version → {new_ver}")
    print(f"\nDone! Restart the server, then:\n  /give @s {full_id}")
    return full_id


def edit_planet(
    name: str,
    block: str | None = None,
    radius: int | None = None,
    ring_block: str | None = None,
    color: str | None = None,
) -> str:
    """Edit an existing planet. Returns full_id. Raises ValueError if not found."""
    if not any([block, radius, ring_block, color]):
        raise ValueError("Provide at least one of block, radius, ring_block, or color to edit.")

    match = _resolve_planet(name)
    full_id  = match["id"]
    item_key = "space_" + full_id.removeprefix("space:")

    new_block      = block      or match["block"]
    new_ring_block = ring_block if ring_block is not None else match["ring_block"]
    new_radius     = radius     or int(match["radius"])

    js = MAIN_JS.read_text()
    entry = f"  '{full_id}': {{ radius: {new_radius}, block: '{new_block}', name: '{match['name']}'"
    if new_ring_block:
        entry += f", ringBlock: '{new_ring_block}'"
    entry += " },"

    old_pattern = re.compile(rf"  '{re.escape(full_id)}':\s*\{{[^}}]+\}},")
    if not old_pattern.search(js):
        raise ValueError(f"Could not find PLANETS entry for {full_id} in main.js")
    MAIN_JS.write_text(old_pattern.sub(entry, js))
    print(f"✓ Updated {full_id} in main.js")

    base_color = parse_hex(color) if color else color_for_block(new_block)
    out = generate_icon(item_key, base_color, new_ring_block)
    print(f"✓ Regenerated {out.relative_to(PACK_DIR)}")

    new_ver = bump_rp_version()
    print(f"✓ Bumped RP version → {new_ver}")
    print(f"\nDone! Restart the server to apply changes.")
    return full_id


def delete_planet(name: str) -> str:
    """Delete a planet by name or ID slug. Returns full_id. Raises ValueError if not found."""
    match    = _resolve_planet(name)
    full_id  = match["id"]
    slug     = full_id.removeprefix("space:")
    item_key = f"space_{slug}"

    # 1. Remove PLANETS entry from main.js
    js = MAIN_JS.read_text()
    old_pattern = re.compile(rf"\n  '{re.escape(full_id)}':\s*\{{[^}}]+\}},")
    if not old_pattern.search(js):
        raise ValueError(f"Could not find PLANETS entry for {full_id} in main.js")
    MAIN_JS.write_text(old_pattern.sub("", js))
    print(f"✓ Removed {full_id} from main.js")

    # 2. Remove entry from item_texture.json
    tex = json.loads(TEXTURE_JSON.read_text())
    tex["texture_data"].pop(item_key, None)
    TEXTURE_JSON.write_text(json.dumps(tex, indent=2) + "\n")
    print(f"✓ Removed {item_key} from item_texture.json")

    # 3. Delete item JSON
    item_file = ITEMS_DIR / f"{item_key}.json"
    if item_file.exists():
        item_file.unlink()
        print(f"✓ Deleted {item_file.relative_to(PACK_DIR)}")

    # 4. Delete icon PNG
    icon_file = TEXTURES_DIR / f"{item_key}.png"
    if icon_file.exists():
        icon_file.unlink()
        print(f"✓ Deleted {icon_file.relative_to(PACK_DIR)}")

    # 5. Bump RP version
    new_ver = bump_rp_version()
    print(f"✓ Bumped RP version → {new_ver}")
    print(f"\nDone! Restart the server to apply changes.")
    return full_id


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add or edit a planet in the Planet Generator pack.",
        epilog=(
            "Add:    uv run add_planet.py 'Haumea' --radius 3 --block white_wool\n"
            "Edit:   uv run add_planet.py 'Earth' --edit --block blue_concrete\n"
            "Delete: uv run add_planet.py 'Haumea' --delete\n"
            "TUI:    uv run tui.py"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("name", nargs="?", help="Display name (e.g. 'Pluto')")
    parser.add_argument("--radius", type=int, help="Radius in blocks")
    parser.add_argument("--block", help="Default block ID (e.g. blue_ice, orange_wool)")
    parser.add_argument("--id", dest="planet_id", help="Item ID slug (auto-derived from name if omitted)")
    parser.add_argument("--ring-block", help="Add rings using this block (e.g. white_wool)")
    parser.add_argument("--color", metavar="HEX", help="Icon base color as hex (e.g. 4488ff). Guessed from block if omitted.")
    parser.add_argument("--list", action="store_true", help="List existing planets and exit")
    parser.add_argument("--edit", action="store_true", help="Edit an existing planet instead of adding a new one")
    parser.add_argument("--delete", action="store_true", help="Delete an existing planet by name or ID slug")

    args = parser.parse_args()

    if args.list:
        list_planets()
        return

    if args.delete:
        if not args.name:
            parser.error("planet name or ID is required with --delete")
        try:
            delete_planet(args.name)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        return

    if args.edit:
        if not args.name:
            parser.error("planet name is required with --edit")
        try:
            edit_planet(
                name=args.name,
                block=args.block,
                radius=args.radius,
                ring_block=args.ring_block,
                color=args.color,
            )
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        return

    if not args.name or not args.radius or not args.block:
        parser.error("name, --radius, and --block are required")

    try:
        add_planet(
            name=args.name,
            radius=args.radius,
            block=args.block,
            ring_block=args.ring_block,
            color=args.color,
            planet_id=args.planet_id,
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
