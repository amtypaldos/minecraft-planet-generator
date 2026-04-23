"""Generate 32x32 planet item textures for the Planet Generator resource pack."""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

SIZE = 32
OUT_DIR = Path(__file__).parent / "planet_generator_rp/textures/items"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PLANETS = {
    "space_sun": {
        "base": (255, 210, 30),
        "highlight": (255, 255, 180),
        "shadow": (220, 100, 0),
        "bands": [(255, 180, 20, 0.3), (255, 240, 80, 0.2)],
    },
    "space_mercury": {
        "base": (150, 140, 135),
        "highlight": (200, 195, 190),
        "shadow": (80, 75, 70),
        "bands": [],
    },
    "space_venus": {
        "base": (230, 200, 120),
        "highlight": (255, 240, 180),
        "shadow": (160, 120, 60),
        "bands": [(220, 180, 90, 0.25), (240, 220, 140, 0.2)],
    },
    "space_earth": {
        "base": (40, 100, 200),
        "highlight": (100, 160, 255),
        "shadow": (20, 50, 120),
        "bands": [(30, 160, 60, 0.4), (20, 130, 50, 0.3)],  # green land patches
    },
    "space_mars": {
        "base": (190, 80, 40),
        "highlight": (240, 150, 100),
        "shadow": (110, 40, 20),
        "bands": [(170, 60, 30, 0.3)],
    },
    "space_jupiter": {
        "base": (210, 160, 110),
        "highlight": (240, 200, 160),
        "shadow": (130, 90, 60),
        "bands": [
            (180, 120, 70, 0.5),
            (230, 180, 130, 0.4),
            (160, 100, 60, 0.4),
            (200, 150, 100, 0.35),
        ],
    },
    "space_saturn": {
        "base": (220, 200, 140),
        "highlight": (255, 240, 190),
        "shadow": (150, 130, 80),
        "bands": [(200, 175, 110, 0.4), (230, 215, 160, 0.35)],
        "rings": True,
    },
    "space_uranus": {
        "base": (100, 210, 220),
        "highlight": (180, 240, 250),
        "shadow": (50, 140, 160),
        "bands": [(80, 190, 205, 0.3)],
    },
    "space_neptune": {
        "base": (40, 80, 200),
        "highlight": (80, 130, 255),
        "shadow": (20, 40, 130),
        "bands": [(30, 60, 180, 0.4), (60, 100, 220, 0.3)],
    },
}


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_planet(name, cfg):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy, r = SIZE / 2, SIZE / 2, SIZE / 2 - 1
    has_rings = cfg.get("rings", False)
    planet_r = r * 0.72 if has_rings else r

    rng = random.Random(name)  # deterministic per planet

    # Draw horizontal bands onto a sphere layer
    band_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bl_draw = ImageDraw.Draw(band_layer)

    for bx in range(SIZE):
        for by in range(SIZE):
            dx, dy = bx - cx, by - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > planet_r:
                continue

            # Latitude on sphere (-1 to 1)
            lat = dy / planet_r
            # Base sphere color with shading
            shade = 1.0 - 0.5 * (dx * 0.6 + dy * 0.3) / planet_r  # directional light
            shade = max(0.3, min(1.2, shade))

            base = lerp_color(cfg["shadow"], cfg["base"], min(1.0, shade))

            # Apply band colors based on latitude
            pixel = base
            for band_color in cfg["bands"]:
                bc, alpha = band_color[:3], band_color[3]
                # Wavy band pattern
                wave = math.sin(lat * math.pi * (2.5 + rng.random() * 1.5) + rng.random())
                if wave > 0.1:
                    t = (wave - 0.1) / 0.9 * alpha
                    pixel = lerp_color(pixel, bc, t * shade)

            # Atmosphere highlight at limb
            limb = max(0, 1.0 - dist / planet_r)
            if limb < 0.15:
                pixel = lerp_color(cfg["highlight"], pixel, limb / 0.15)

            # Specular highlight (top-left)
            spec_dx, spec_dy = bx - cx * 0.55, by - cy * 0.55
            spec_dist = math.sqrt(spec_dx * spec_dx + spec_dy * spec_dy)
            spec = max(0.0, 1.0 - spec_dist / (planet_r * 0.45)) ** 2
            r_ch = min(255, int(pixel[0] + spec * 80))
            g_ch = min(255, int(pixel[1] + spec * 80))
            b_ch = min(255, int(pixel[2] + spec * 80))

            bl_draw.point((bx, by), (r_ch, g_ch, b_ch, 255))

    img.paste(band_layer, (0, 0), band_layer)

    # Rings for Saturn
    if has_rings:
        ring_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        rl_draw = ImageDraw.Draw(ring_layer)
        ring_color = (200, 180, 120)
        for bx in range(SIZE):
            for by in range(SIZE):
                dx, dy = bx - cx, by - cy
                # Flatten y to simulate tilt
                edx = dx
                edy = dy / 0.35
                dist = math.sqrt(edx * edx + edy * edy)
                if planet_r * 1.25 <= dist <= planet_r * 1.9 and abs(dy) < planet_r * 0.25:
                    # Don't draw ring in front of planet's bottom half
                    if dy > 0 and math.sqrt(dx*dx + dy*dy) < planet_r:
                        continue
                    alpha_fade = 1.0 - abs(dist - planet_r * 1.6) / (planet_r * 0.35)
                    alpha = int(max(0, min(180, alpha_fade * 180)))
                    rl_draw.point((bx, by), ring_color + (alpha,))
        # Slight blur on rings for softness
        ring_layer = ring_layer.filter(ImageFilter.GaussianBlur(0.5))
        img = Image.alpha_composite(img, ring_layer)

    out = OUT_DIR / f"{name}.png"
    img.save(out)
    print(f"  {name}.png")


print("Generating planet textures...")
for planet_name, planet_cfg in PLANETS.items():
    make_planet(planet_name, planet_cfg)
print(f"Done → {OUT_DIR}")
