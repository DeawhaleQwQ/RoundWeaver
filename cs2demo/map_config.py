from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


DEFAULT_MAP_NAME = "de_dust2"
DEFAULT_OVERVIEW_PATH = Path("assets/maps/de_dust2/de_dust2.txt")
DEFAULT_RADAR_PATH = Path("assets/maps/de_dust2/de_dust2_radar.png")


@dataclass(frozen=True)
class Dust2MapConfig:
    map_name: str
    pos_x: float
    pos_y: float
    scale: float
    rotate: float | None = None
    zoom: float | None = None
    radar_path: Path = DEFAULT_RADAR_PATH

    def game_to_radar(self, x: float, y: float) -> tuple[float, float]:
        return game_to_radar(x, y, self)

    def radar_to_game(self, x: float, y: float) -> tuple[float, float]:
        return radar_to_game(x, y, self)


def _overview_pairs(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        line = line.split("//", 1)[0].strip()
        if not line or line in {"{", "}"}:
            continue
        matches = re.findall(r'"([^"]+)"', line)
        if len(matches) >= 2:
            pairs[matches[0]] = matches[1]
        elif len(matches) == 1 and matches[0].startswith("de_"):
            pairs["map_name"] = matches[0]
    return pairs


def load_dust2_config(
    overview_path: str | Path = DEFAULT_OVERVIEW_PATH,
    radar_path: str | Path = DEFAULT_RADAR_PATH,
) -> Dust2MapConfig:
    overview = Path(overview_path)
    if not overview.exists():
        raise FileNotFoundError(f"Dust2 overview file not found: {overview}")

    values = _overview_pairs(overview.read_text(encoding="utf-8"))
    missing = [key for key in ("pos_x", "pos_y", "scale") if key not in values]
    if missing:
        raise ValueError(f"Dust2 overview is missing required keys: {missing}")

    map_name = values.get("map_name", DEFAULT_MAP_NAME)
    if map_name != DEFAULT_MAP_NAME:
        raise ValueError(f"Only {DEFAULT_MAP_NAME} is supported, got {map_name}")

    return Dust2MapConfig(
        map_name=map_name,
        pos_x=float(values["pos_x"]),
        pos_y=float(values["pos_y"]),
        scale=float(values["scale"]),
        rotate=float(values["rotate"]) if "rotate" in values else None,
        zoom=float(values["zoom"]) if "zoom" in values else None,
        radar_path=Path(radar_path),
    )


def game_to_radar(x: float, y: float, cfg: Dust2MapConfig) -> tuple[float, float]:
    img_x = (x - cfg.pos_x) / cfg.scale
    img_y = (cfg.pos_y - y) / cfg.scale
    return img_x, img_y


def radar_to_game(x: float, y: float, cfg: Dust2MapConfig) -> tuple[float, float]:
    game_x = x * cfg.scale + cfg.pos_x
    game_y = cfg.pos_y - y * cfg.scale
    return game_x, game_y
