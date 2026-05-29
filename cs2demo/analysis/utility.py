from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any
import json

from demoparser2 import DemoParser

from cs2demo.map_config import Dust2MapConfig
from cs2demo.parser import clean_record, find_round_for_tick, frame_to_records, stringify_id, to_float, to_int

UTILITY_WEAPONS = {
    "weapon_smokegrenade": "smoke",
    "weapon_flashbang": "flashbang",
    "weapon_hegrenade": "hegrenade",
    "weapon_molotov": "molotov",
    "weapon_incgrenade": "molotov",
    "weapon_decoy": "decoy",
}
PROJECTILE_TYPES = {
    "CSmokeGrenadeProjectile": "smoke",
    "CFlashbangProjectile": "flashbang",
    "CHEGrenadeProjectile": "hegrenade",
    "CMolotovProjectile": "molotov",
    "CDecoyProjectile": "decoy",
}
DETONATE_EVENTS = {
    "smokegrenade_detonate": "smoke",
    "flashbang_detonate": "flashbang",
    "hegrenade_detonate": "hegrenade",
    "inferno_startburn": "molotov",
    "decoy_detonate": "decoy",
}
EXPIRE_EVENTS = {
    "smokegrenade_expired": "smoke",
    "inferno_expire": "molotov",
}
UTILITY_RELEVANT_EVENTS = set(DETONATE_EVENTS) | set(EXPIRE_EVENTS) | {"weapon_fire", "player_blind", "player_hurt"}
UTILITY_DAMAGE_WEAPON_NAMES = ("hegrenade", "molotov", "incgrenade", "inferno", "fire")
PRECISE_TRAJECTORY_MAX_DEMO_BYTES = 250 * 1024 * 1024
UTILITY_COLORS = {
    "smoke": "#d1d5db",
    "flashbang": "#ffffff",
    "hegrenade": "#ef4444",
    "molotov": "#f97316",
    "decoy": "#a78bfa",
}
DEFAULT_UTILITY_EFFECTS = {
    "flashbang": {
        "flash_visual_duration_sec": 0.8,
        "flash_core_radius": 160,
        "flash_fade_radius": 500,
        "max_blind_duration_sec": 5.0,
    },
    "hegrenade": {
        "blast_visual_duration_sec": 0.7,
        "smoke_visual_duration_sec": 2.5,
        "damage_radius": 350,
        "inner_radius": 120,
        "outer_radius": 350,
    },
    "smoke": {
        "duration_sec": 18.0,
        "radius": 170,
        "fade_in_sec": 1.0,
        "fade_out_sec": 1.5,
        "core_color": "rgba(55, 55, 55, 0.62)",
        "outer_color": "rgba(95, 95, 95, 0.34)",
        "edge_color": "rgba(120, 120, 120, 0.18)",
        "t_core_color": "rgba(255, 177, 66, 0.68)",
        "t_outer_color": "rgba(245, 158, 11, 0.40)",
        "t_edge_color": "rgba(251, 191, 36, 0.20)",
        "ct_core_color": "rgba(96, 165, 250, 0.68)",
        "ct_outer_color": "rgba(59, 130, 246, 0.40)",
        "ct_edge_color": "rgba(147, 197, 253, 0.20)",
        "timer_bg_color": "rgba(15, 17, 23, 0.72)",
        "timer_fill_color": "rgba(238, 242, 247, 0.82)",
        "timer_text_color": "rgba(255, 255, 255, 0.88)",
    },
    "molotov": {
        "duration_sec": 7.0,
        "max_duration_sec": 7.5,
        "radius": 180,
        "fade_in_sec": 0.5,
        "fade_out_sec": 0.8,
    },
    "decoy": {
        "duration_sec": 8.0,
        "radius": 90,
        "fade_in_sec": 0.2,
        "fade_out_sec": 0.5,
    },
}




def load_utility_effect_config(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    config = deepcopy(DEFAULT_UTILITY_EFFECTS)
    if path is None:
        return config
    config_path = Path(path)
    if not config_path.exists():
        return config
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    for utility_type, values in payload.items():
        if not isinstance(values, dict):
            continue
        config.setdefault(utility_type, {})
        config[utility_type].update(values)
    return config


def seconds_to_ticks(seconds: Any, tick_rate: float) -> int:
    value = to_float(seconds)
    if value is None:
        return 0
    return int(round(value * tick_rate))


def utility_config(config: dict[str, dict[str, Any]] | None, utility_type: str) -> dict[str, Any]:
    source = config or DEFAULT_UTILITY_EFFECTS
    if utility_type == "incgrenade":
        utility_type = "molotov"
    return source.get(utility_type, {})


def build_utility_events(
    demo_path: str | Path,
    rounds: list[dict[str, Any]],
    events_by_type: dict[str, list[dict[str, Any]]],
    map_cfg: Dust2MapConfig,
    tick_rate: float = 64.0,
    max_points_per_trajectory: int = 96,
    effect_config: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    effect_config = effect_config or load_utility_effect_config()
    projectile_groups = parse_projectile_groups(demo_path, rounds, map_cfg, max_points_per_trajectory)
    expire_by_entity = index_events_by_entity(events_by_type, EXPIRE_EVENTS)
    weapon_fires = build_weapon_fire_index(events_by_type.get("weapon_fire", []))
    blinds = events_by_type.get("player_blind", [])
    hurts = events_by_type.get("player_hurt", [])

    utilities = []
    used_projectiles: set[tuple[str, str | None, int]] = set()
    for event_name, utility_type in DETONATE_EVENTS.items():
        for detonate in events_by_type.get(event_name, []):
            projectile = matching_projectile(projectile_groups, utility_type, detonate, used_projectiles, tick_rate)
            if projectile is not None:
                used_projectiles.add(projectile_key(projectile))
            entity_id = (projectile or {}).get("entity_id") or stringify_id(detonate.get("entityid"))
            expire = nearest_event(expire_by_entity.get((utility_type, entity_id), []), detonate.get("tick"))
            if expire is None and projectile is not None:
                expire = nearest_lifecycle_event(events_by_type, EXPIRE_EVENTS, utility_type, projectile, tick_rate, tick=detonate.get("tick"))
            fire_tick = (projectile or {}).get("first_tick") or detonate.get("tick")
            fire = nearest_weapon_fire(weapon_fires.get((utility_type, stringify_id(detonate.get("user_steamid"))), []), fire_tick)
            utilities.append(
                build_utility_event(
                    utility_type=utility_type,
                    sequence=len(utilities) + 1,
                    rounds=rounds,
                    map_cfg=map_cfg,
                    tick_rate=tick_rate,
                    projectile=projectile,
                    fire=fire,
                    detonate=detonate,
                    expire=expire,
                    blinds=blinds,
                    hurts=hurts,
                    approximate=projectile is None,
                    effect_config=effect_config,
                )
            )

    return sort_utility_events(utilities)


def build_utility_events_bounded(
    demo_path: str | Path,
    rounds: list[dict[str, Any]],
    events_by_type: dict[str, list[dict[str, Any]]],
    map_cfg: Dust2MapConfig,
    tick_rate: float = 64.0,
    max_points_per_trajectory: int = 96,
    effect_config: dict[str, dict[str, Any]] | None = None,
    trajectory_mode: str = "auto",
) -> list[dict[str, Any]]:
    effect_config = effect_config or load_utility_effect_config()
    events_by_type = {name: events_by_type.get(name, []) for name in UTILITY_RELEVANT_EVENTS}
    projectile_groups = []
    if should_parse_precise_projectiles(demo_path, trajectory_mode):
        try:
            projectile_groups = parse_projectile_groups(demo_path, rounds, map_cfg, max_points_per_trajectory)
        except Exception:
            if trajectory_mode == "precise":
                raise
            projectile_groups = []
    expire_by_entity = index_events_by_entity(events_by_type, EXPIRE_EVENTS)
    weapon_fires = build_weapon_fire_index(events_by_type.get("weapon_fire", []))
    blinds_by_tick = sorted_events(events_by_type.get("player_blind", []))
    hurts_by_tick = sorted_events(events_by_type.get("player_hurt", []))

    detonation_rows: list[tuple[int, str, dict[str, Any]]] = []
    for event_name, utility_type in DETONATE_EVENTS.items():
        for detonate in events_by_type.get(event_name, []):
            tick = to_int(detonate.get("tick"))
            if tick is None:
                continue
            detonation_rows.append((tick, utility_type, detonate))
    detonation_rows.sort(key=lambda row: (row[0], row[1]))

    utilities = []
    used_projectiles: set[tuple[str, str | None, int]] = set()
    for _, utility_type, detonate in detonation_rows:
        projectile = matching_projectile(projectile_groups, utility_type, detonate, used_projectiles, tick_rate) if projectile_groups else None
        if projectile is not None:
            used_projectiles.add(projectile_key(projectile))
        entity_id = (projectile or {}).get("entity_id") or stringify_id(detonate.get("entityid"))
        expire = nearest_event(expire_by_entity.get((utility_type, entity_id), []), detonate.get("tick"))
        if expire is None and projectile is not None:
            expire = nearest_lifecycle_event(events_by_type, EXPIRE_EVENTS, utility_type, projectile, tick_rate, tick=detonate.get("tick"))
        fire_tick = (projectile or {}).get("first_tick") or detonate.get("tick")
        fire = nearest_weapon_fire_window(weapon_fires.get((utility_type, stringify_id(detonate.get("user_steamid"))), []), fire_tick)
        utility = build_utility_event(
            utility_type=utility_type,
            sequence=len(utilities) + 1,
            rounds=rounds,
            map_cfg=map_cfg,
            tick_rate=tick_rate,
            projectile=projectile,
            fire=fire,
            detonate=detonate,
            expire=expire,
            blinds=events_in_tick_window(blinds_by_tick, detonate.get("tick"), int(tick_rate * 2)),
            hurts=events_in_tick_window(hurts_by_tick, detonate.get("tick"), int(tick_rate * 2)),
            approximate=projectile is None,
            effect_config=effect_config,
        )
        utilities.append(utility)
    return sort_utility_events(utilities)


def sort_utility_events(utilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(utilities, key=lambda row: (row.get("round_number") or 0, row.get("throw_tick") or row.get("detonate_tick") or 0, row.get("id") or ""))


def should_parse_precise_projectiles(demo_path: str | Path, trajectory_mode: str) -> bool:
    if trajectory_mode == "approximate":
        return False
    if trajectory_mode == "precise":
        return True
    try:
        return Path(demo_path).stat().st_size <= PRECISE_TRAJECTORY_MAX_DEMO_BYTES
    except OSError:
        return False


def sorted_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((event for event in events if to_int(event.get("tick")) is not None), key=lambda event: to_int(event.get("tick")) or -1)


def events_in_tick_window(events: list[dict[str, Any]], tick: Any, window: int) -> list[dict[str, Any]]:
    target = to_int(tick)
    if target is None:
        return []
    start = target - window
    end = target + window
    left = lower_bound_tick(events, start)
    right = lower_bound_tick(events, end + 1)
    return events[left:right]


def lower_bound_tick(events: list[dict[str, Any]], target: int) -> int:
    left = 0
    right = len(events)
    while left < right:
        mid = (left + right) // 2
        if (to_int(events[mid].get("tick")) or -1) < target:
            left = mid + 1
        else:
            right = mid
    return left


def nearest_weapon_fire_window(events: list[dict[str, Any]], tick: Any) -> dict[str, Any] | None:
    target = to_int(tick)
    if target is None:
        return events[-1] if events else None
    idx = lower_bound_tick(events, target + 1)
    if idx > 0:
        return events[idx - 1]
    return events[0] if events else None


def summarize_utility_events(utility_events: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = defaultdict(int)
    precise = 0
    approximate = 0
    for event in utility_events:
        by_type[str(event.get("type") or "unknown")] += 1
        if event.get("approximate_trajectory"):
            approximate += 1
        else:
            precise += 1
    return {"total": len(utility_events), "by_type": dict(sorted(by_type.items())), "precise": precise, "approximate": approximate}


def utility_markers(utility_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers = []
    for utility in utility_events:
        if utility.get("round_number") is None:
            continue
        if utility.get("throw_tick") is not None:
            markers.append(make_marker(utility, "utility_throw", utility["throw_tick"], f"{utility['type']} throw"))
        if utility.get("detonate_tick") is not None:
            markers.append(make_marker(utility, "utility_detonate", utility["detonate_tick"], f"{utility['type']} detonate"))
        effect = utility.get("effect") or {}
        if effect.get("start_tick") is not None:
            marker = make_marker(utility, "utility_effect", effect["start_tick"], f"{utility['type']} effect")
            marker["end_tick"] = effect.get("end_tick")
            markers.append(marker)
    return markers


def make_marker(utility: dict[str, Any], marker_type: str, tick: int, label: str) -> dict[str, Any]:
    return {
        "type": marker_type,
        "utility_type": utility.get("type"),
        "round_number": utility.get("round_number"),
        "tick": tick,
        "label": label,
        "team": None,
        "payload": {"utility_id": utility.get("id"), "approximate_trajectory": utility.get("approximate_trajectory")},
    }


def parse_projectile_groups(demo_path: str | Path, rounds: list[dict[str, Any]], map_cfg: Dust2MapConfig, max_points: int) -> list[dict[str, Any]]:
    parser = DemoParser(str(demo_path))
    frame = parser.parse_grenades()
    records = [clean_record(row) for row in frame_to_records(frame)]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        projectile_type = row.get("grenade_type")
        utility_type = PROJECTILE_TYPES.get(str(projectile_type))
        entity_id = stringify_id(row.get("grenade_entity_id"))
        tick = to_int(row.get("tick"))
        if utility_type is None or entity_id is None or tick is None:
            continue
        grouped[(utility_type, entity_id)].append(row)

    groups = []
    for (utility_type, entity_id), rows in grouped.items():
        rows = sorted(rows, key=lambda row: to_int(row.get("tick")) or -1)
        for segment_index, segment in enumerate(split_projectile_segments(rows)):
            points = [projectile_point(row, map_cfg) for row in segment]
            points = [point for point in points if point is not None]
            if not points:
                continue
            sampled = sample_points(points, max_points)
            first = points[0]
            last = points[-1]
            groups.append(
                {
                    "type": utility_type,
                    "entity_id": entity_id,
                    "segment_index": segment_index,
                    "thrower_steamid": stringify_id(segment[0].get("steamid")),
                    "thrower": segment[0].get("name"),
                    "first_tick": first["tick"],
                    "last_tick": last["tick"],
                    "throw_pos": first["pos"],
                    "detonate_pos": last["pos"],
                    "radar_throw_pos": first["radar_pos"],
                    "radar_detonate_pos": last["radar_pos"],
                    "trajectory": sampled,
                }
            )
    return groups


def split_projectile_segments(rows: list[dict[str, Any]], max_gap: int = 128) -> list[list[dict[str, Any]]]:
    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    previous_tick: int | None = None
    for row in rows:
        tick = to_int(row.get("tick"))
        if tick is None:
            continue
        if current and previous_tick is not None and tick - previous_tick > max_gap:
            segments.append(current)
            current = []
        current.append(row)
        previous_tick = tick
    if current:
        segments.append(current)
    return segments


def projectile_point(row: dict[str, Any], map_cfg: Dust2MapConfig) -> dict[str, Any] | None:
    tick = to_int(row.get("tick"))
    x = to_float(row.get("x"))
    y = to_float(row.get("y"))
    z = to_float(row.get("z"))
    if tick is None or x is None or y is None:
        return None
    radar_x, radar_y = map_cfg.game_to_radar(x, y)
    return {"tick": tick, "pos": pos(x, y, z), "radar_pos": radar_pos(radar_x, radar_y)}


def sample_points(points: list[dict[str, Any]], max_points: int) -> list[dict[str, Any]]:
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    sampled = points[::step]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled[:max_points - 1] + [points[-1]] if len(sampled) > max_points else sampled


def matching_projectile(
    projectiles: list[dict[str, Any]],
    utility_type: str,
    detonate: dict[str, Any],
    used: set[tuple[str, str | None, int]],
    tick_rate: float,
) -> dict[str, Any] | None:
    detonate_tick = to_int(detonate.get("tick"))
    thrower = stringify_id(detonate.get("user_steamid"))
    entity_id = stringify_id(detonate.get("entityid"))
    candidates = []
    for projectile in projectiles:
        if projectile.get("type") != utility_type or projectile_key(projectile) in used:
            continue
        if thrower and projectile.get("thrower_steamid") and projectile.get("thrower_steamid") != thrower:
            continue
        if entity_id and projectile.get("entity_id") == entity_id:
            candidates.append(projectile)
            continue
        last_tick = to_int(projectile.get("last_tick"))
        if detonate_tick is not None and last_tick is not None and abs(last_tick - detonate_tick) <= int(tick_rate * 4):
            candidates.append(projectile)
    return min(candidates, key=lambda projectile: abs((to_int(projectile.get("last_tick")) or 0) - (detonate_tick or 0)), default=None)


def projectile_key(projectile: dict[str, Any]) -> tuple[str, str | None, int]:
    return (str(projectile.get("type")), stringify_id(projectile.get("entity_id")), to_int(projectile.get("first_tick")) or 0)


def index_events_by_entity(events_by_type: dict[str, list[dict[str, Any]]], mapping: dict[str, str]) -> dict[tuple[str, str | None], list[dict[str, Any]]]:
    indexed: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for event_name, utility_type in mapping.items():
        for event in events_by_type.get(event_name, []):
            indexed[(utility_type, stringify_id(event.get("entityid")))].append(event)
    return indexed


def build_weapon_fire_index(events: list[dict[str, Any]]) -> dict[tuple[str, str | None], list[dict[str, Any]]]:
    indexed: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        weapon = event.get("weapon") or event.get("weapon_name")
        utility_type = UTILITY_WEAPONS.get(str(weapon))
        if utility_type is None:
            continue
        indexed[(utility_type, stringify_id(event.get("user_steamid")))].append(event)
    for rows in indexed.values():
        rows.sort(key=lambda row: to_int(row.get("tick")) or -1)
    return indexed


def nearest_lifecycle_event(
    events_by_type: dict[str, list[dict[str, Any]]],
    mapping: dict[str, str],
    utility_type: str,
    projectile: dict[str, Any],
    tick_rate: float,
    tick: Any | None = None,
) -> dict[str, Any] | None:
    target_tick = to_int(tick) if tick is not None else to_int(projectile.get("last_tick"))
    thrower = stringify_id(projectile.get("thrower_steamid"))
    candidates = []
    for event_name, mapped_type in mapping.items():
        if mapped_type != utility_type:
            continue
        for event in events_by_type.get(event_name, []):
            event_tick = to_int(event.get("tick"))
            if event_tick is None:
                continue
            if thrower and stringify_id(event.get("user_steamid")) and stringify_id(event.get("user_steamid")) != thrower:
                continue
            candidates.append(event)
    return nearest_event(candidates, target_tick, max_gap=int(tick_rate * 4))


def nearest_event(events: list[dict[str, Any]], tick: Any, max_gap: int | None = None) -> dict[str, Any] | None:
    target = to_int(tick)
    candidates = [event for event in events if to_int(event.get("tick")) is not None]
    if target is None:
        return candidates[0] if candidates else None
    best = min(candidates, key=lambda event: abs((to_int(event.get("tick")) or 0) - target), default=None)
    if best is None:
        return None
    if max_gap is not None and abs((to_int(best.get("tick")) or 0) - target) > max_gap:
        return None
    return best


def nearest_weapon_fire(events: list[dict[str, Any]], tick: Any) -> dict[str, Any] | None:
    target = to_int(tick)
    if target is None:
        return events[-1] if events else None
    before = [event for event in events if (to_int(event.get("tick")) or 0) <= target]
    if before:
        return before[-1]
    return nearest_event(events, target)


def build_utility_event(
    utility_type: str,
    sequence: int,
    rounds: list[dict[str, Any]],
    map_cfg: Dust2MapConfig,
    tick_rate: float,
    projectile: dict[str, Any] | None,
    fire: dict[str, Any] | None,
    detonate: dict[str, Any] | None,
    expire: dict[str, Any] | None,
    blinds: list[dict[str, Any]],
    hurts: list[dict[str, Any]],
    approximate: bool,
    effect_config: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    throw_tick = to_int(projectile.get("first_tick")) if projectile else to_int(fire.get("tick")) if fire else None
    detonate_tick = to_int(detonate.get("tick")) if detonate else to_int(projectile.get("last_tick")) if projectile else throw_tick
    expire_tick = validated_expire_tick(utility_type, detonate_tick, expire, tick_rate, effect_config)
    used_demo_expire_tick = expire_tick is not None and expire is not None and expire_tick == to_int(expire.get("tick"))
    if expire_tick is None:
        expire_tick = default_expire_tick(utility_type, detonate_tick, tick_rate, effect_config)
    used_fallback_duration = not used_demo_expire_tick and expire_tick is not None
    round_number = find_round_for_tick(detonate_tick or throw_tick, rounds) or to_int((detonate or fire or {}).get("round"))

    thrower_steamid = stringify_id((projectile or {}).get("thrower_steamid")) or stringify_id((fire or detonate or {}).get("user_steamid"))
    thrower = (projectile or {}).get("thrower") or (fire or detonate or {}).get("user_name")
    throw_pos = (projectile or {}).get("throw_pos") or event_pos(fire, map_cfg) or event_pos(detonate, map_cfg)
    detonate_pos = event_pos(detonate, map_cfg) or (projectile or {}).get("detonate_pos") or throw_pos
    radar_throw_pos = (projectile or {}).get("radar_throw_pos") or radar_from_pos(throw_pos, map_cfg)
    radar_detonate_pos = radar_from_pos(detonate_pos, map_cfg) or (projectile or {}).get("radar_detonate_pos") or radar_throw_pos
    trajectory = (projectile or {}).get("trajectory") or interpolate_trajectory(throw_tick, detonate_tick, throw_pos, detonate_pos, radar_throw_pos, radar_detonate_pos)

    utility_id = f"u{sequence:04d}_{utility_type}_{round_number or 0}_{detonate_tick or throw_tick or 0}"
    effect = build_effect(
        utility_type,
        detonate_tick,
        expire_tick,
        detonate_pos,
        radar_detonate_pos,
        detonate,
        blinds,
        hurts,
        tick_rate,
        effect_config,
        used_demo_expire_tick,
        used_fallback_duration,
    )
    return {
        "id": utility_id,
        "source": "demo",
        "round_number": round_number,
        "type": utility_type,
        "thrower_steamid": thrower_steamid,
        "thrower_player_id": thrower_steamid,
        "thrower": thrower,
        "entity_id": (projectile or {}).get("entity_id") or stringify_id((detonate or {}).get("entityid")),
        "throw_tick": throw_tick,
        "detonate_tick": detonate_tick,
        "expire_tick": expire_tick,
        "throw_pos": throw_pos,
        "detonate_pos": detonate_pos,
        "radar_throw_pos": radar_throw_pos,
        "radar_detonate_pos": radar_detonate_pos,
        "trajectory": trajectory,
        "approximate_trajectory": bool(approximate),
        "effect": effect,
    }


def build_effect(
    utility_type: str,
    detonate_tick: int | None,
    expire_tick: int | None,
    detonate_pos: dict[str, Any] | None,
    radar_detonate_pos: dict[str, Any] | None,
    detonate: dict[str, Any] | None,
    blinds: list[dict[str, Any]],
    hurts: list[dict[str, Any]],
    tick_rate: float,
    effect_config: dict[str, dict[str, Any]],
    used_demo_expire_tick: bool,
    used_fallback_duration: bool,
) -> dict[str, Any]:
    cfg = utility_config(effect_config, utility_type)
    start_tick = detonate_tick
    if utility_type == "flashbang":
        end_tick = detonate_tick + seconds_to_ticks(cfg.get("flash_visual_duration_sec", 0.8), tick_rate) if detonate_tick is not None else expire_tick
        radius = cfg.get("flash_fade_radius", 500)
    elif utility_type == "hegrenade":
        visual_ticks = max(seconds_to_ticks(cfg.get("blast_visual_duration_sec", 0.7), tick_rate), seconds_to_ticks(cfg.get("smoke_visual_duration_sec", 2.5), tick_rate))
        end_tick = detonate_tick + visual_ticks if detonate_tick is not None else expire_tick
        radius = cfg.get("damage_radius", cfg.get("outer_radius", 350))
    else:
        end_tick = expire_tick
        radius = cfg.get("radius", 100)
    blinded_players = flash_targets(detonate, blinds, tick_rate, cfg) if utility_type == "flashbang" else []
    damaged_players = damage_targets(detonate, hurts, tick_rate) if utility_type in {"hegrenade", "molotov"} else []
    effect = {
        "type": utility_type,
        "color": UTILITY_COLORS.get(utility_type, "#ffffff"),
        "radius": radius,
        "inner_radius": cfg.get("inner_radius"),
        "outer_radius": cfg.get("outer_radius") or cfg.get("damage_radius") or cfg.get("radius"),
        "damage_radius": cfg.get("damage_radius"),
        "flash_core_radius": cfg.get("flash_core_radius"),
        "flash_fade_radius": cfg.get("flash_fade_radius"),
        "fade_in_ticks": seconds_to_ticks(cfg.get("fade_in_sec", 0), tick_rate),
        "fade_out_ticks": seconds_to_ticks(cfg.get("fade_out_sec", 0), tick_rate),
        "start_tick": start_tick,
        "end_tick": end_tick,
        "pos": detonate_pos,
        "radar_pos": radar_detonate_pos,
        "target_players": blinded_players,
        "blinded_players": blinded_players,
        "damaged_players": damaged_players,
        "used_demo_expire_tick": used_demo_expire_tick,
        "used_fallback_duration": used_fallback_duration,
    }
    return effect


def flash_targets(detonate: dict[str, Any] | None, blinds: list[dict[str, Any]], tick_rate: float, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    if detonate is None:
        return []
    detonate_tick = to_int(detonate.get("tick"))
    entity_id = stringify_id(detonate.get("entityid"))
    attacker = stringify_id(detonate.get("user_steamid"))
    targets = []
    for blind in blinds:
        blind_tick = to_int(blind.get("tick"))
        if detonate_tick is None or blind_tick is None or abs(blind_tick - detonate_tick) > int(tick_rate * 2):
            continue
        blind_entity = stringify_id(blind.get("entityid"))
        blind_attacker = stringify_id(blind.get("attacker_steamid")) or stringify_id(blind.get("user_steamid"))
        if entity_id and blind_entity and entity_id != blind_entity:
            continue
        if not entity_id and attacker and blind_attacker and attacker != blind_attacker:
            continue
        raw_duration = to_float(blind.get("blind_duration")) or to_float(blind.get("duration"))
        approximate = raw_duration is None
        duration = raw_duration if raw_duration is not None else 1.0
        max_duration = to_float(cfg.get("max_blind_duration_sec")) or 5.0
        intensity = max(0.0, min(1.0, duration / max_duration))
        targets.append(
            {
                "steamid": stringify_id(blind.get("user_steamid")) or stringify_id(blind.get("steamid")),
                "name": blind.get("user_name") or blind.get("name"),
                "tick": blind_tick,
                "end_tick": blind_tick + int(duration * tick_rate),
                "duration": round(duration, 2),
                "intensity": round(intensity, 3),
                "approximate": approximate,
            }
        )
    return targets


def damage_targets(detonate: dict[str, Any] | None, hurts: list[dict[str, Any]], tick_rate: float) -> list[dict[str, Any]]:
    if detonate is None:
        return []
    detonate_tick = to_int(detonate.get("tick"))
    attacker = stringify_id(detonate.get("user_steamid"))
    targets = []
    for hurt in hurts:
        hurt_tick = to_int(hurt.get("tick"))
        if detonate_tick is None or hurt_tick is None or abs(hurt_tick - detonate_tick) > int(tick_rate * 2):
            continue
        hurt_attacker = stringify_id(hurt.get("attacker_steamid")) or stringify_id(hurt.get("user_steamid"))
        if attacker and hurt_attacker and attacker != hurt_attacker:
            continue
        weapon = str(hurt.get("weapon") or hurt.get("weapon_name") or "").lower()
        if weapon and not any(name in weapon for name in ("hegrenade", "molotov", "incgrenade", "inferno", "fire")):
            continue
        targets.append(
            {
                "steamid": stringify_id(hurt.get("user_steamid")) or stringify_id(hurt.get("steamid")),
                "name": hurt.get("user_name") or hurt.get("name"),
                "tick": hurt_tick,
                "damage": to_int(hurt.get("dmg_health")) or to_int(hurt.get("damage")),
                "weapon": hurt.get("weapon") or hurt.get("weapon_name"),
            }
        )
    return targets


def validated_expire_tick(
    utility_type: str,
    detonate_tick: int | None,
    expire: dict[str, Any] | None,
    tick_rate: float,
    effect_config: dict[str, dict[str, Any]] | None = None,
) -> int | None:
    expire_tick = to_int(expire.get("tick")) if expire else None
    if expire_tick is None or detonate_tick is None:
        return expire_tick
    if expire_tick <= detonate_tick:
        return None
    cfg = utility_config(effect_config, utility_type)
    max_duration = to_float(cfg.get("max_duration_sec"))
    if max_duration is not None and expire_tick - detonate_tick > seconds_to_ticks(max_duration, tick_rate):
        return None
    return expire_tick


def default_expire_tick(utility_type: str, detonate_tick: int | None, tick_rate: float, effect_config: dict[str, dict[str, Any]] | None = None) -> int | None:
    if detonate_tick is None:
        return None
    cfg = utility_config(effect_config, utility_type)
    if utility_type == "flashbang":
        seconds = cfg.get("flash_visual_duration_sec", 0.8)
    elif utility_type == "hegrenade":
        seconds = max(to_float(cfg.get("blast_visual_duration_sec")) or 0.7, to_float(cfg.get("smoke_visual_duration_sec")) or 2.5)
    else:
        seconds = cfg.get("duration_sec", 1.0)
    return detonate_tick + seconds_to_ticks(seconds, tick_rate)


def expire_event_for_type(utility_type: str) -> str | None:
    for event_name, mapped_type in EXPIRE_EVENTS.items():
        if mapped_type == utility_type:
            return event_name
    return None


def event_pos(event: dict[str, Any] | None, map_cfg: Dust2MapConfig) -> dict[str, Any] | None:
    if not event:
        return None
    x = to_float(event.get("x"))
    y = to_float(event.get("y"))
    z = to_float(event.get("z"))
    if x is None or y is None:
        return None
    return pos(x, y, z)


def radar_from_pos(position: dict[str, Any] | None, map_cfg: Dust2MapConfig) -> dict[str, float] | None:
    if not position:
        return None
    x = to_float(position.get("x"))
    y = to_float(position.get("y"))
    if x is None or y is None:
        return None
    radar_x, radar_y = map_cfg.game_to_radar(x, y)
    return radar_pos(radar_x, radar_y)


def interpolate_trajectory(
    throw_tick: int | None,
    detonate_tick: int | None,
    throw_pos: dict[str, Any] | None,
    detonate_pos: dict[str, Any] | None,
    radar_throw_pos: dict[str, Any] | None,
    radar_detonate_pos: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if throw_tick is None or detonate_tick is None or not throw_pos or not detonate_pos or not radar_throw_pos or not radar_detonate_pos:
        return []
    if throw_tick == detonate_tick:
        return [{"tick": throw_tick, "pos": throw_pos, "radar_pos": radar_throw_pos}]
    points = []
    steps = 12
    for idx in range(steps + 1):
        ratio = idx / steps
        tick = round(throw_tick + (detonate_tick - throw_tick) * ratio)
        points.append(
            {
                "tick": tick,
                "pos": lerp_pos(throw_pos, detonate_pos, ratio),
                "radar_pos": lerp_pos(radar_throw_pos, radar_detonate_pos, ratio),
            }
        )
    return points


def lerp_pos(start: dict[str, Any], end: dict[str, Any], ratio: float) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in start.keys() | end.keys():
        a = to_float(start.get(key))
        b = to_float(end.get(key))
        result[key] = round(a + (b - a) * ratio, 3) if a is not None and b is not None else a if b is None else b
    return result


def pos(x: float, y: float, z: float | None) -> dict[str, float | None]:
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3) if z is not None else None}


def radar_pos(x: float, y: float) -> dict[str, float]:
    return {"x": round(x, 2), "y": round(y, 2)}
