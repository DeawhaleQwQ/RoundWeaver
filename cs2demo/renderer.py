from __future__ import annotations

from pathlib import Path
import logging

from PIL import Image, ImageDraw

from cs2demo.map_config import Dust2MapConfig, load_dust2_config
from cs2demo.parser import Cs2DemoParser, to_float


DEFAULT_POINT_RADIUS = 5


def render_kills_map(
    demo_path: str | Path,
    out_path: str | Path,
    overview_path: str | Path,
    radar_path: str | Path,
    logger: logging.Logger | None = None,
) -> Path:
    log = logger or logging.getLogger(__name__)
    cfg = load_dust2_config(overview_path=overview_path, radar_path=radar_path)
    if not cfg.radar_path.exists():
        raise FileNotFoundError(f"Dust2 radar image not found: {cfg.radar_path}")

    _, kills = Cs2DemoParser(demo_path, logger=log).parse_kills_for_render()
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(cfg.radar_path).convert("RGBA") as image:
        draw = ImageDraw.Draw(image)
        drawn, skipped = draw_kill_points(draw, kills, cfg, image.size)
        image.save(output)

    log.info("Rendered %d kill points to %s; skipped %d without valid coordinates", drawn, output, skipped)
    return output


def draw_kill_points(
    draw: ImageDraw.ImageDraw,
    kills: list[dict],
    cfg: Dust2MapConfig,
    image_size: tuple[int, int],
) -> tuple[int, int]:
    width, height = image_size
    drawn = 0
    skipped = 0
    for kill in kills:
        x = to_float(kill.get("x") if kill.get("x") is not None else kill.get("X"))
        y = to_float(kill.get("y") if kill.get("y") is not None else kill.get("Y"))
        if x is None or y is None:
            skipped += 1
            continue
        img_x, img_y = cfg.game_to_radar(x, y)
        if img_x < 0 or img_y < 0 or img_x > width or img_y > height:
            skipped += 1
            continue
        draw_point(draw, img_x, img_y, kill)
        drawn += 1
    return drawn, skipped


def draw_point(draw: ImageDraw.ImageDraw, x: float, y: float, kill: dict) -> None:
    radius = DEFAULT_POINT_RADIUS
    headshot = bool(kill.get("headshot"))
    fill = (255, 50, 50, 230) if not headshot else (255, 220, 50, 240)
    outline = (10, 10, 10, 255)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=outline, width=2)
    if headshot:
        draw.line((x - radius, y, x + radius, y), fill=outline, width=1)
        draw.line((x, y - radius, x, y + radius), fill=outline, width=1)
