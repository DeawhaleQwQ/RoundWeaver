from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import math
import re
import secrets
import shutil

import pandas as pd
from PIL import Image

from cs2demo.analysis.utility import build_utility_events_bounded, load_utility_effect_config, summarize_utility_events, utility_markers
from cs2demo.map_config import DEFAULT_OVERVIEW_PATH, DEFAULT_RADAR_PATH, load_dust2_config
from cs2demo.parser import to_float, to_int, write_json
from cs2demo.pipeline import ensure_analysis_outputs

REPLAY_VERSION = "0.7.0"
UTILITY_EVENT_NAMES = {
    "smokegrenade_detonate",
    "flashbang_detonate",
    "hegrenade_detonate",
    "inferno_startburn",
    "decoy_detonate",
    "smokegrenade_expired",
    "inferno_expire",
    "weapon_fire",
    "player_blind",
    "player_hurt",
}
TICK_COLUMNS = [
    "tick",
    "round",
    "name",
    "steamid",
    "team",
    "side",
    "X",
    "Y",
    "Z",
    "yaw",
    "health",
    "armor",
    "is_alive",
    "active_weapon_name",
    "has_bomb",
    "balance",
    "equip_value",
    "weapons",
    "cash_spent",
]
ROOM_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
NOTEBOOK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
TEAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    samples_dir: Path
    outputs_dir: Path
    assets_dir: Path
    web_dir: Path


def project_paths() -> ProjectPaths:
    root = Path(__file__).resolve().parents[1]
    return ProjectPaths(
        root=root,
        samples_dir=root / "samples" / "demos",
        outputs_dir=root / "outputs",
        assets_dir=root / "assets",
        web_dir=Path(__file__).resolve().parent / "web",
    )


def list_demos(paths: ProjectPaths | None = None) -> list[dict[str, Any]]:
    paths = paths or project_paths()
    demos = []
    for demo_path in sorted(paths.samples_dir.glob("*.dem")):
        demos.append({"demo_id": demo_path.stem, "filename": demo_path.name, "path": str(demo_path.relative_to(paths.root))})
    return demos


def resolve_demo_path(demo_id: str, paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    allowed = {demo["demo_id"]: paths.root / demo["path"] for demo in list_demos(paths)}
    if demo_id not in allowed:
        raise KeyError(f"Unknown demo_id: {demo_id}")
    return allowed[demo_id]


def demo_output_dir(demo_id: str, paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    return paths.outputs_dir if demo_id == "test_dust2" else paths.outputs_dir / demo_id


def replay_cache_dir(demo_id: str, paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    return paths.outputs_dir / "web" / demo_id


def rooms_dir(paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    return paths.outputs_dir / "rooms"


def normalize_room_code(room_code: str) -> str:
    code = str(room_code or "")
    if not ROOM_CODE_PATTERN.fullmatch(code):
        raise KeyError(f"Unknown room_code: {room_code}")
    return code


def room_state_path(room_code: str, paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    directory = rooms_dir(paths).resolve()
    path = (directory / f"{normalize_room_code(room_code)}.json").resolve()
    if path.parent != directory:
        raise KeyError(f"Unknown room_code: {room_code}")
    return path


def ensure_replay_cache(
    demo_id: str,
    tick_interval: int = 8,
    tick_rate: float = 64.0,
    scope: str = "auto",
    force: bool = False,
    paths: ProjectPaths | None = None,
    trajectory_mode: str = "auto",
) -> Path:
    paths = paths or project_paths()
    demo_path = resolve_demo_path(demo_id, paths)
    out_dir = demo_output_dir(demo_id, paths)
    ensure_analysis_outputs(demo_path, out_dir, tick_interval=tick_interval, tick_rate=tick_rate, scope=scope)
    cache_dir = replay_cache_dir(demo_id, paths)
    manifest_path = cache_dir / "replay.json"
    if force or replay_manifest_stale(manifest_path):
        build_replay_cache(demo_id, out_dir, cache_dir, demo_path, tick_rate=tick_rate, paths=paths, trajectory_mode=trajectory_mode)
    return manifest_path


def replay_manifest_stale(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        manifest = read_json(path)
    except Exception:
        return True
    if manifest.get("schema_version") != REPLAY_VERSION:
        return True
    if manifest.get("export", {}).get("complete") is False:
        return True
    rounds_dir = path.parent / "rounds"
    for round_row in manifest.get("rounds", []):
        round_number = to_int(round_row.get("round"))
        if round_number is not None and not (rounds_dir / f"{round_number}.json").exists():
            return True
    return False


def build_replay_cache(
    demo_id: str,
    out_dir: Path,
    cache_dir: Path,
    demo_path: Path,
    tick_rate: float = 64.0,
    paths: ProjectPaths | None = None,
    trajectory_mode: str = "auto",
) -> dict[str, Any]:
    paths = paths or project_paths()
    cache_dir.mkdir(parents=True, exist_ok=True)
    rounds_dir = cache_dir / "rounds"
    if rounds_dir.exists():
        shutil.rmtree(rounds_dir)
    rounds_dir.mkdir(parents=True, exist_ok=True)

    summary = read_json(out_dir / "summary.json")
    findings_payload = read_json(out_dir / "findings.json")
    metrics = read_json(out_dir / "player_metrics.json")
    ticks_path = out_dir / "ticks.parquet"
    if not ticks_path.exists():
        ticks_path = out_dir / "ticks.csv"

    map_cfg = load_dust2_config(paths.root / DEFAULT_OVERVIEW_PATH, paths.root / DEFAULT_RADAR_PATH)
    width, height = image_size(paths.root / DEFAULT_RADAR_PATH)
    rounds = summary.get("rounds", [])
    findings = compact_findings(findings_payload.get("findings", []))
    utility_effects = load_utility_effect_config(paths.root / "config" / "utility_effects.json")
    round_numbers = {to_int(round_row.get("round")) for round_row in rounds}
    round_numbers.discard(None)
    utility_events = [
        utility
        for utility in build_utility_events_bounded(
            demo_path,
            rounds,
            events_by_type(out_dir / "events.jsonl", event_names=UTILITY_EVENT_NAMES),
            map_cfg,
            tick_rate=tick_rate,
            effect_config=utility_effects,
            trajectory_mode=trajectory_mode,
        )
        if to_int(utility.get("round_number")) in round_numbers
    ]
    utilities_by_round = group_rows_by_round(utility_events, "round_number")
    base_markers = group_markers_by_round(build_markers(summary, findings, []))
    frame_counts: dict[int, int] = {}
    score_table = round_score_table(rounds)

    for round_info in rounds:
        round_number = to_int(round_info.get("round"))
        if round_number is None:
            continue
        tick_group = read_round_ticks(ticks_path, round_number)
        frames = build_round_frames_streamed(tick_group, map_cfg)
        frame_counts[round_number] = len(frames)
        round_utilities = enrich_approximate_utility_trajectories(utilities_by_round.get(round_number, []), frames, map_cfg)
        markers = sorted(
            base_markers.get(round_number, []) + utility_markers(round_utilities),
            key=lambda row: (row.get("tick") or 0, row.get("type") or ""),
        )
        write_json_atomic(
            rounds_dir / f"{round_number}.json",
            {
                "round": round_number,
                "start_tick": round_info.get("start_tick"),
                "freeze_end_tick": round_info.get("freeze_end_tick"),
                "end_tick": round_info.get("end_tick"),
                "utility_events": round_utilities,
                "markers": markers,
                "frames": frames,
                "economy": build_round_economy(round_info, frames),
                "score": score_table.get(round_number),
            },
        )

    manifest = {
        "schema_version": REPLAY_VERSION,
        "demo_id": demo_id,
        "demo_path": str(demo_path.relative_to(paths.root)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "export": {
            "complete": True,
            "source_size_bytes": demo_path.stat().st_size,
            "source_mtime": datetime.fromtimestamp(demo_path.stat().st_mtime, timezone.utc).isoformat(),
            "completed_rounds": sorted(frame_counts),
            "trajectory_mode": trajectory_mode,
        },
        "match": {
            "header": summary.get("match_header", {}),
            "player_stats": summary.get("player_stats", []),
            "metrics": metrics,
        },
        "map": {
            "name": map_cfg.map_name,
            "radar_url": "/assets/maps/de_dust2/de_dust2_radar.png",
            "pos_x": map_cfg.pos_x,
            "pos_y": map_cfg.pos_y,
            "scale": map_cfg.scale,
            "width": width,
            "height": height,
        },
        "players": summary.get("players", []),
        "rounds": round_manifest_from_counts(rounds, frame_counts, demo_id),
        "findings": findings,
        "utility_effects": utility_effects,
        "utility_summary": summarize_utility_events(utility_events),
    }
    write_json_atomic(cache_dir / "replay.json", manifest)
    return manifest


ECONOMY_TICK_COLUMNS = ["balance", "equip_value", "weapons", "cash_spent"]


def _available_tick_columns(path: Path) -> list[str]:
    """Return the subset of TICK_COLUMNS actually present in the file.

    Older ticks.parquet/csv (pre-economy) lack balance/equip_value/weapons/
    cash_spent; requesting them would raise. We read only what exists and fill
    the rest with None downstream so callers see a uniform schema."""
    try:
        if path.suffix == ".parquet":
            import pyarrow.parquet as pq

            # Use read_schema (top-level field names) — ParquetFile.schema.names
            # flattens list columns to their inner field (e.g. "weapons" -> "element").
            schema_names = set(pq.read_schema(path).names)
        else:
            header = pd.read_csv(path, nrows=0)
            schema_names = set(header.columns)
    except Exception:
        return [col for col in TICK_COLUMNS if col not in ECONOMY_TICK_COLUMNS]
    return [col for col in TICK_COLUMNS if col in schema_names]


def _ensure_tick_columns(frame: pd.DataFrame) -> pd.DataFrame:
    for col in TICK_COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    return frame


def read_ticks(path: Path) -> pd.DataFrame:
    columns = _available_tick_columns(path)
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path, columns=columns)
    else:
        frame = pd.read_csv(path, usecols=columns)
    return normalize_ticks_frame(_ensure_tick_columns(frame))


def read_round_ticks(path: Path, round_number: int) -> pd.DataFrame:
    columns = _available_tick_columns(path)
    if path.suffix == ".parquet":
        try:
            frame = pd.read_parquet(path, columns=columns, filters=[("round", "==", round_number)])
        except Exception:
            frame = pd.read_parquet(path, columns=columns)
            frame = frame[frame["round"] == round_number]
        return normalize_ticks_frame(_ensure_tick_columns(frame))

    chunks = []
    for chunk in pd.read_csv(path, usecols=columns, chunksize=250_000):
        chunk = chunk[chunk["round"] == round_number]
        if not chunk.empty:
            chunks.append(chunk)
    if not chunks:
        return _ensure_tick_columns(pd.DataFrame(columns=columns))
    return normalize_ticks_frame(_ensure_tick_columns(pd.concat(chunks, ignore_index=True)))


def normalize_ticks_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame[frame["round"].notna()].copy()
    frame["round"] = frame["round"].astype(int)
    frame["tick"] = frame["tick"].astype(int)
    return frame.sort_values(["round", "tick", "steamid"])


def build_round_frames(group: pd.DataFrame, map_cfg: Any) -> list[dict[str, Any]]:
    return build_round_frames_streamed(group, map_cfg)


def build_round_frames_streamed(group: pd.DataFrame, map_cfg: Any) -> list[dict[str, Any]]:
    frames = []
    for tick, tick_group in group.groupby("tick", sort=True):
        players = []
        for row in tick_group.itertuples(index=False):
            row_data = row._asdict()
            x = clean_number(row_data.get("X"))
            y = clean_number(row_data.get("Y"))
            if x is None or y is None:
                continue
            radar_x, radar_y = map_cfg.game_to_radar(x, y)
            weapons_raw = row_data.get("weapons")
            if weapons_raw is None:
                weapons = []
            elif isinstance(weapons_raw, (list, tuple)):
                weapons = [str(item) for item in weapons_raw if item is not None]
            elif hasattr(weapons_raw, "tolist"):
                weapons = [str(item) for item in weapons_raw.tolist() if item is not None]
            else:
                weapons = []
            players.append(
                {
                    "steamid": str(row_data["steamid"]),
                    "name": clean_scalar(row_data.get("name")),
                    "team": clean_scalar(row_data.get("team")),
                    "side": clean_scalar(row_data.get("side")),
                    "x": x,
                    "y": y,
                    "z": clean_number(row_data.get("Z")),
                    "radar_x": round(radar_x, 2),
                    "radar_y": round(radar_y, 2),
                    "yaw": clean_number(row_data.get("yaw")),
                    "health": clean_int(row_data.get("health")),
                    "armor": clean_int(row_data.get("armor")),
                    "is_alive": clean_bool(row_data.get("is_alive")),
                    "active_weapon_name": clean_scalar(row_data.get("active_weapon_name")),
                    "has_bomb": clean_bool(row_data.get("has_bomb")),
                    "balance": clean_int(row_data.get("balance")),
                    "equip_value": clean_int(row_data.get("equip_value")),
                    "weapons": weapons,
                    "cash_spent": clean_int(row_data.get("cash_spent")),
                }
            )
        frames.append({"tick": int(tick), "players": players})
    return frames


LOSS_BONUS_LADDER = [1400, 1900, 2400, 2900, 3400]


def round_score_table(rounds: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Running scoreboard + next-round loss bonus per round, derived purely from
    the round-end winner sequence (no parser prop dependency).

    For each round we record the cumulative T/CT side score AFTER that round,
    plus the projected next-round loss bonus for each side from the consecutive
    loss ladder [1400,1900,2400,2900,3400]."""
    table: dict[int, dict[str, Any]] = {}
    t_score = 0
    ct_score = 0
    t_loss_streak = 0
    ct_loss_streak = 0
    for round_row in sorted(rounds, key=lambda r: to_int(r.get("round")) or 0):
        round_number = to_int(round_row.get("round"))
        if round_number is None:
            continue
        winner = (round_row.get("winner_side") or "").upper()
        if winner == "T":
            t_score += 1
            t_loss_streak = 0
            ct_loss_streak = min(ct_loss_streak + 1, len(LOSS_BONUS_LADDER))
        elif winner == "CT":
            ct_score += 1
            ct_loss_streak = 0
            t_loss_streak = min(t_loss_streak + 1, len(LOSS_BONUS_LADDER))
        next_t_bonus = LOSS_BONUS_LADDER[min(max(t_loss_streak, 1), len(LOSS_BONUS_LADDER)) - 1]
        next_ct_bonus = LOSS_BONUS_LADDER[min(max(ct_loss_streak, 1), len(LOSS_BONUS_LADDER)) - 1]
        table[round_number] = {
            "round": round_number,
            "t_score": t_score,
            "ct_score": ct_score,
            "winner_side": winner or None,
            "reason": round_row.get("reason"),
            "next_loss_bonus": {"T": next_t_bonus, "CT": next_ct_bonus},
            "t_loss_streak": t_loss_streak,
            "ct_loss_streak": ct_loss_streak,
        }
    return table


def build_round_economy(round_info: dict[str, Any], frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-round economy snapshot at the freeze-end (buy-locked) frame: each
    team's per-player balance/equip_value/weapons plus team totals."""
    freeze_end = to_int(round_info.get("freeze_end_tick"))
    snapshot_frame = None
    if freeze_end is not None:
        for frame in frames:
            frame_tick = to_int(frame.get("tick"))
            if frame_tick is not None and frame_tick >= freeze_end:
                snapshot_frame = frame
                break
    if snapshot_frame is None and frames:
        snapshot_frame = frames[0]
    teams = {
        "T": {"players": [], "team_balance": 0, "team_equip_value": 0},
        "CT": {"players": [], "team_balance": 0, "team_equip_value": 0},
    }
    for player in (snapshot_frame or {}).get("players", []):
        side = (player.get("side") or player.get("team") or "").upper()
        if side not in teams:
            continue
        balance = player.get("balance")
        equip = player.get("equip_value")
        teams[side]["players"].append(
            {
                "steamid": player.get("steamid"),
                "name": player.get("name"),
                "balance": balance,
                "equip_value": equip,
                "weapons": player.get("weapons") or [],
            }
        )
        if isinstance(balance, int):
            teams[side]["team_balance"] += balance
        if isinstance(equip, int):
            teams[side]["team_equip_value"] += equip
    return {"snapshot_tick": to_int((snapshot_frame or {}).get("tick")), "T": teams["T"], "CT": teams["CT"]}


def round_manifest(rounds: list[dict[str, Any]], ticks: pd.DataFrame, demo_id: str) -> list[dict[str, Any]]:
    frame_counts = ticks.groupby("round")["tick"].nunique().to_dict()
    return round_manifest_from_counts(rounds, {int(key): int(value) for key, value in frame_counts.items()}, demo_id)


def round_manifest_from_counts(rounds: list[dict[str, Any]], frame_counts: dict[int, int], demo_id: str) -> list[dict[str, Any]]:
    score_table = round_score_table(rounds)
    return [
        {
            **round_row,
            "frame_count": int(frame_counts.get(to_int(round_row.get("round")) or -1, 0)),
            "round_url": f"/api/demos/{demo_id}/rounds/{round_row.get('round')}",
            "score": score_table.get(to_int(round_row.get("round"))),
        }
        for round_row in rounds
    ]


def enrich_approximate_utility_trajectories(utilities: list[dict[str, Any]], frames: list[dict[str, Any]], map_cfg: Any) -> list[dict[str, Any]]:
    if not utilities or not frames:
        return utilities
    for utility in utilities:
        if not utility.get("approximate_trajectory"):
            continue
        detonate_pos = utility.get("detonate_pos")
        radar_detonate_pos = utility.get("radar_detonate_pos") or utility.get("effect", {}).get("radar_pos")
        thrower = utility.get("thrower_player_id") or utility.get("thrower_steamid")
        throw_tick = to_int(utility.get("throw_tick"))
        player = nearest_player_before_tick(frames, thrower, throw_tick)
        if not player or not detonate_pos or not radar_detonate_pos:
            continue
        throw_pos = {"x": player.get("x"), "y": player.get("y"), "z": player.get("z")}
        radar_throw_pos = {"x": player.get("radar_x"), "y": player.get("radar_y")}
        if not valid_radar_pos(radar_throw_pos) or not valid_radar_pos(radar_detonate_pos):
            continue
        if radar_distance(radar_throw_pos, radar_detonate_pos) < 2:
            continue
        utility["throw_pos"] = throw_pos
        utility["radar_throw_pos"] = radar_throw_pos
        utility["trajectory"] = approximate_arc_trajectory(
            to_int(utility.get("throw_tick")),
            to_int(utility.get("detonate_tick")),
            throw_pos,
            detonate_pos,
            radar_throw_pos,
            radar_detonate_pos,
        )
    return utilities


def nearest_player_before_tick(frames: list[dict[str, Any]], steamid: Any, tick: int | None) -> dict[str, Any] | None:
    if steamid is None:
        return None
    target = tick if tick is not None else frames[0].get("tick")
    best_player = None
    best_delta = None
    for frame in frames:
        frame_tick = to_int(frame.get("tick"))
        if frame_tick is None or target is None:
            continue
        delta = abs(frame_tick - target)
        if frame_tick > target and best_player is not None:
            break
        for player in frame.get("players", []):
            if str(player.get("steamid")) != str(steamid):
                continue
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_player = player
            break
    return best_player


def approximate_arc_trajectory(
    throw_tick: int | None,
    detonate_tick: int | None,
    throw_pos: dict[str, Any],
    detonate_pos: dict[str, Any],
    radar_throw_pos: dict[str, Any],
    radar_detonate_pos: dict[str, Any],
) -> list[dict[str, Any]]:
    if throw_tick is None or detonate_tick is None or detonate_tick <= throw_tick:
        detonate_tick = (throw_tick or 0) + 1
    points = []
    steps = 12
    for idx in range(steps + 1):
        ratio = idx / steps
        arc = math.sin(math.pi * ratio)
        tick = round(throw_tick + (detonate_tick - throw_tick) * ratio)
        pos = lerp_dict(throw_pos, detonate_pos, ratio)
        radar_pos = lerp_dict(radar_throw_pos, radar_detonate_pos, ratio)
        if pos.get("z") is not None:
            pos["z"] = round(float(pos["z"]) + arc * 120, 3)
        radar_pos["y"] = round(float(radar_pos["y"]) - arc * 24, 2)
        points.append({"tick": tick, "pos": pos, "radar_pos": radar_pos})
    return points


def lerp_dict(start: dict[str, Any], end: dict[str, Any], ratio: float) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in start.keys() | end.keys():
        a = to_float(start.get(key))
        b = to_float(end.get(key))
        result[key] = round(a + (b - a) * ratio, 3) if a is not None and b is not None else a if b is None else b
    return result


def valid_radar_pos(point: dict[str, Any] | None) -> bool:
    return point is not None and to_float(point.get("x")) is not None and to_float(point.get("y")) is not None


def radar_distance(start: dict[str, Any], end: dict[str, Any]) -> float:
    x1 = to_float(start.get("x")) or 0
    y1 = to_float(start.get("y")) or 0
    x2 = to_float(end.get("x")) or 0
    y2 = to_float(end.get("y")) or 0
    return math.hypot(x2 - x1, y2 - y1)


def build_markers(summary: dict[str, Any], findings: list[dict[str, Any]], utility_events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    markers = []
    for kill in summary.get("key_events", {}).get("kills", []):
        round_number = to_int(kill.get("round"))
        tick = to_int(kill.get("tick"))
        if round_number is None or tick is None:
            continue
        markers.append(
            {
                "type": "kill",
                "round_number": round_number,
                "tick": tick,
                "label": f"{kill.get('attacker_name')} -> {kill.get('user_name')}",
                "team": None,
                "payload": {
                    "attacker": kill.get("attacker_name"),
                    "victim": kill.get("user_name"),
                    "weapon": kill.get("weapon"),
                    "headshot": kill.get("headshot"),
                },
            }
        )
    for bomb in summary.get("key_events", {}).get("bomb", []):
        round_number = to_int(bomb.get("round"))
        tick = to_int(bomb.get("tick"))
        if round_number is None or tick is None:
            continue
        markers.append(
            {
                "type": bomb.get("event_type") or "bomb",
                "round_number": round_number,
                "tick": tick,
                "label": f"{bomb.get('event_type')} {bomb.get('user_name') or ''}".strip(),
                "team": "T" if bomb.get("event_type") == "bomb_planted" else "CT",
                "payload": bomb,
            }
        )
    for finding in findings:
        if finding.get("round_number") is None or finding.get("jump_tick") is None:
            continue
        markers.append(
            {
                "type": "finding",
                "finding_type": finding.get("finding_type"),
                "round_number": finding.get("round_number"),
                "tick": finding.get("jump_tick"),
                "label": finding.get("title"),
                "team": finding.get("team"),
                "payload": {"finding_id": finding.get("finding_id"), "severity": finding.get("severity")},
            }
        )
    markers.extend(utility_markers(utility_events or []))
    return sorted(markers, key=lambda row: (row.get("round_number") or 0, row.get("tick") or 0, row.get("type") or ""))


def compact_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "finding_id": finding.get("finding_id"),
            "finding_type": finding.get("finding_type"),
            "title": finding.get("title"),
            "sentiment": finding.get("sentiment"),
            "severity": finding.get("severity"),
            "team": finding.get("team"),
            "round_number": finding.get("round_number"),
            "tick": finding.get("tick"),
            "jump_tick": finding.get("jump_tick"),
            "players": finding.get("players", []),
            "message": finding.get("message"),
            "evidence": finding.get("evidence", {}),
        }
        for finding in findings
    ]


def events_by_type(path: Path, event_names: set[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not path.exists():
        return grouped
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            event_type = row.get("event_type") or "unknown"
            if event_names is not None and event_type not in event_names:
                continue
            grouped.setdefault(event_type, []).append(row)
    return grouped


def group_rows_by_round(rows: list[dict[str, Any]], field: str) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        round_number = to_int(row.get(field))
        if round_number is not None:
            grouped.setdefault(round_number, []).append(row)
    return grouped


def group_markers_by_round(markers: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    return group_rows_by_round(markers, "round_number")


def write_json_atomic(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    write_json(tmp_path, data)
    tmp_path.replace(path)


def generate_room_code(paths: ProjectPaths | None = None) -> str:
    paths = paths or project_paths()
    rooms_dir(paths).mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        code = secrets.token_urlsafe(12)
        if len(code) >= 10 and ROOM_CODE_PATTERN.fullmatch(code) and not room_state_path(code, paths).exists():
            return code
    raise RuntimeError("Could not allocate room code")


def parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def room_last_activity_at(room: dict[str, Any]) -> datetime | None:
    candidates = [
        parse_iso_datetime(room.get("last_activity_at")),
        parse_iso_datetime(room.get("updated_at")),
        parse_iso_datetime(room.get("created_at")),
    ]
    participants = room.get("participants", {})
    if isinstance(participants, dict):
        for participant in participants.values():
            if isinstance(participant, dict):
                candidates.append(parse_iso_datetime(participant.get("last_seen_at")))
    valid = [candidate for candidate in candidates if candidate is not None]
    if valid:
        return max(valid)
    return parse_iso_datetime(room.get("updated_at"))


def room_is_expired(room: dict[str, Any], idle_ttl_sec: float | None) -> bool:
    if not idle_ttl_sec or idle_ttl_sec <= 0:
        return False
    now = datetime.now(timezone.utc)
    participants = room.get("participants", {})
    if isinstance(participants, dict):
        for participant in participants.values():
            if not isinstance(participant, dict) or not participant.get("online"):
                continue
            last_seen = parse_iso_datetime(participant.get("last_seen_at"))
            if last_seen is None or (now - last_seen).total_seconds() <= idle_ttl_sec:
                return False
    last_activity = room_last_activity_at(room)
    if last_activity is None:
        return False
    return (now - last_activity).total_seconds() > idle_ttl_sec


def delete_room_state(room_code: str, paths: ProjectPaths | None = None) -> None:
    path = room_state_path(room_code, paths)
    if path.exists():
        path.unlink()


def purge_expired_rooms(paths: ProjectPaths | None = None, idle_ttl_sec: float | None = None) -> list[str]:
    paths = paths or project_paths()
    directory = rooms_dir(paths)
    if not directory.exists() or not idle_ttl_sec or idle_ttl_sec <= 0:
        return []
    deleted = []
    for path in directory.glob("*.json"):
        try:
            room = read_json(path)
            code = normalize_room_code(room.get("room_code") or path.stem)
        except Exception:
            continue
        if room_is_expired(room, idle_ttl_sec):
            delete_room_state(code, paths)
            deleted.append(code)
    return deleted


def load_room_state(room_code: str, paths: ProjectPaths | None = None, idle_ttl_sec: float | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    path = room_state_path(room_code, paths)
    if not path.exists():
        raise KeyError(f"Unknown room_code: {room_code}")
    room = read_json(path)
    if room_is_expired(room, idle_ttl_sec):
        delete_room_state(room_code, paths)
        raise KeyError(f"Unknown room_code: {room_code}")
    return room


def save_room_state(room: dict[str, Any], paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    code = normalize_room_code(room.get("room_code") or room.get("code"))
    now = datetime.now(timezone.utc).isoformat()
    state = dict(room)
    state["room_code"] = code
    state["updated_at"] = now
    state.setdefault("created_at", now)
    state.setdefault("last_activity_at", state.get("created_at") or now)
    rooms_dir(paths).mkdir(parents=True, exist_ok=True)
    write_json_atomic(room_state_path(code, paths), state)
    return state


def list_room_states(paths: ProjectPaths | None = None, idle_ttl_sec: float | None = None) -> list[dict[str, Any]]:
    paths = paths or project_paths()
    purge_expired_rooms(paths, idle_ttl_sec)
    directory = rooms_dir(paths)
    if not directory.exists():
        return []
    rooms = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            room = read_json(path)
            code = normalize_room_code(room.get("room_code") or path.stem)
        except Exception:
            continue
        if room_is_expired(room, idle_ttl_sec):
            delete_room_state(code, paths)
            continue
        participants = room.get("participants", {})
        online = sum(1 for participant in participants.values() if participant.get("online")) if isinstance(participants, dict) else 0
        rooms.append(
            {
                "room_code": code,
                "title": room.get("title"),
                "demo_id": room.get("demo_id"),
                "mode": room.get("mode", "replay"),
                "version": room.get("version", 0),
                "created_at": room.get("created_at"),
                "updated_at": room.get("updated_at"),
                "last_activity_at": room.get("last_activity_at"),
                "online_count": online,
                "participant_count": len(participants) if isinstance(participants, dict) else 0,
            }
        )
    return rooms


def create_room_state(
    demo_id: str,
    round_number: int | None = None,
    tick: int | None = None,
    title: str | None = None,
    paths: ProjectPaths | None = None,
) -> dict[str, Any]:
    paths = paths or project_paths()
    resolve_demo_path(demo_id, paths)
    manifest_path = ensure_replay_cache(demo_id, paths=paths)
    manifest = read_json(manifest_path)
    rounds = manifest.get("rounds", [])
    if not rounds:
        raise KeyError(f"No rounds for demo_id: {demo_id}")
    indexed_rounds = {to_int(row.get("round")): row for row in rounds if to_int(row.get("round")) is not None}
    selected_round = to_int(round_number) if round_number is not None else next(iter(indexed_rounds))
    if selected_round not in indexed_rounds:
        raise KeyError(f"Unknown round_number: {round_number}")
    round_path = replay_cache_dir(demo_id, paths) / "rounds" / f"{selected_round}.json"
    if not round_path.exists():
        raise KeyError(f"Round not found: {selected_round}")
    round_state = read_json(round_path)
    frames = round_state.get("frames", [])
    first_tick = to_int(frames[0].get("tick")) if frames else to_int(round_state.get("start_tick"))
    last_tick = to_int(frames[-1].get("tick")) if frames else to_int(round_state.get("end_tick"))
    selected_tick = to_int(tick) if tick is not None else first_tick
    if selected_tick is None:
        selected_tick = 0
    if first_tick is not None and selected_tick < first_tick:
        selected_tick = first_tick
    if last_tick is not None and selected_tick > last_tick:
        selected_tick = last_tick
    now = datetime.now(timezone.utc).isoformat()
    room = {
        "schema_version": 1,
        "room_code": generate_room_code(paths),
        "title": title or f"{demo_id} R{selected_round}",
        "demo_id": demo_id,
        "mode": "replay",
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "playback": {
            "round_number": selected_round,
            "tick": selected_tick,
            "is_playing": False,
            "speed": 1,
            "updated_at": now,
            "server_time_ms": None,
        },
        "sandbox": {
            "active": False,
            "source_round_number": selected_round,
            "source_tick": selected_tick,
            "source_frame_index": 0,
            "currentTick": selected_tick,
            "playing": False,
            "tokens": [],
            "annotations": [],
            "planned_utilities": [],
        },
        "participants": {},
        "settings": {"max_participants": 5},
    }
    return save_room_state(room, paths)


def notebooks_dir(paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    return paths.outputs_dir / "notebooks"


def normalize_notebook_id(notebook_id: str) -> str:
    value = str(notebook_id or "")
    if not NOTEBOOK_ID_PATTERN.fullmatch(value):
        raise KeyError(f"Unknown notebook_id: {notebook_id}")
    return value


def notebook_path(notebook_id: str, paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    directory = notebooks_dir(paths).resolve()
    path = (directory / f"{normalize_notebook_id(notebook_id)}.json").resolve()
    if path.parent != directory:
        raise KeyError(f"Unknown notebook_id: {notebook_id}")
    return path


def generate_notebook_id(paths: ProjectPaths | None = None) -> str:
    paths = paths or project_paths()
    notebooks_dir(paths).mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        nid = secrets.token_urlsafe(12)
        if len(nid) >= 10 and NOTEBOOK_ID_PATTERN.fullmatch(nid) and not notebook_path(nid, paths).exists():
            return nid
    raise RuntimeError("Could not allocate notebook id")


def _notebook_preview(body: str, limit: int = 120) -> str:
    text = " ".join(str(body or "").split())
    return text[:limit]


def create_notebook(payload: dict[str, Any] | None = None, paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    payload = payload or {}
    now = datetime.now(timezone.utc).isoformat()
    notebook = {
        "schema_version": 1,
        "notebook_id": generate_notebook_id(paths),
        "title": str(payload.get("title") or "未命名笔记本").strip()[:120] or "未命名笔记本",
        "body": str(payload.get("body") or ""),
        "tags": [str(tag)[:40] for tag in (payload.get("tags") or []) if str(tag).strip()][:20],
        "demo_id": (str(payload.get("demo_id")) if payload.get("demo_id") else None),
        "owner_member_id": (str(payload.get("owner_member_id")) if payload.get("owner_member_id") else None),
        "created_at": now,
        "updated_at": now,
    }
    return save_notebook(notebook, paths)


def save_notebook(notebook: dict[str, Any], paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    nid = normalize_notebook_id(notebook.get("notebook_id"))
    now = datetime.now(timezone.utc).isoformat()
    state = dict(notebook)
    state["notebook_id"] = nid
    state.setdefault("schema_version", 1)
    state.setdefault("created_at", now)
    state["updated_at"] = now
    notebooks_dir(paths).mkdir(parents=True, exist_ok=True)
    write_json_atomic(notebook_path(nid, paths), state)
    return state


def load_notebook(notebook_id: str, paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    path = notebook_path(notebook_id, paths)
    if not path.exists():
        raise KeyError(f"Unknown notebook_id: {notebook_id}")
    return read_json(path)


def update_notebook(notebook_id: str, payload: dict[str, Any], paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    existing = load_notebook(notebook_id, paths)
    if "title" in payload:
        existing["title"] = str(payload.get("title") or "未命名笔记本").strip()[:120] or "未命名笔记本"
    if "body" in payload:
        existing["body"] = str(payload.get("body") or "")
    if "tags" in payload:
        existing["tags"] = [str(tag)[:40] for tag in (payload.get("tags") or []) if str(tag).strip()][:20]
    if "demo_id" in payload:
        existing["demo_id"] = (str(payload.get("demo_id")) if payload.get("demo_id") else None)
    if "owner_member_id" in payload:
        existing["owner_member_id"] = (str(payload.get("owner_member_id")) if payload.get("owner_member_id") else None)
    return save_notebook(existing, paths)


def delete_notebook(notebook_id: str, paths: ProjectPaths | None = None) -> None:
    path = notebook_path(notebook_id, paths)
    if path.exists():
        path.unlink()


def list_notebooks(paths: ProjectPaths | None = None) -> list[dict[str, Any]]:
    paths = paths or project_paths()
    directory = notebooks_dir(paths)
    if not directory.exists():
        return []
    notebooks = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            notebook = read_json(path)
            nid = normalize_notebook_id(notebook.get("notebook_id") or path.stem)
        except Exception:
            continue
        notebooks.append(
            {
                "notebook_id": nid,
                "title": notebook.get("title") or "未命名笔记本",
                "tags": notebook.get("tags") or [],
                "demo_id": notebook.get("demo_id"),
                "owner_member_id": notebook.get("owner_member_id"),
                "preview": _notebook_preview(notebook.get("body")),
                "created_at": notebook.get("created_at"),
                "updated_at": notebook.get("updated_at"),
            }
        )
    return notebooks


def teams_dir(paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    return paths.outputs_dir / "teams"


def normalize_team_id(team_id: str) -> str:
    value = str(team_id or "")
    if not TEAM_ID_PATTERN.fullmatch(value):
        raise KeyError(f"Unknown team_id: {team_id}")
    return value


def team_path(team_id: str, paths: ProjectPaths | None = None) -> Path:
    paths = paths or project_paths()
    directory = teams_dir(paths).resolve()
    path = (directory / f"{normalize_team_id(team_id)}.json").resolve()
    if path.parent != directory:
        raise KeyError(f"Unknown team_id: {team_id}")
    return path


def generate_team_id(paths: ProjectPaths | None = None) -> str:
    paths = paths or project_paths()
    teams_dir(paths).mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        tid = secrets.token_urlsafe(12)
        if len(tid) >= 10 and TEAM_ID_PATTERN.fullmatch(tid) and not team_path(tid, paths).exists():
            return tid
    raise RuntimeError("Could not allocate team id")


def _normalize_member(member: dict[str, Any]) -> dict[str, Any]:
    member = member or {}
    member_id = str(member.get("member_id") or "").strip() or secrets.token_urlsafe(8)
    aliases = [str(a).strip() for a in (member.get("aliases") or []) if str(a).strip()][:20]
    return {
        "member_id": member_id,
        "display_name": str(member.get("display_name") or "").strip()[:60] or "成员",
        "steamid": (str(member.get("steamid")).strip() if member.get("steamid") else None),
        "aliases": aliases,
        "note": str(member.get("note") or "")[:500],
        "profile_notebook_id": (str(member.get("profile_notebook_id")) if member.get("profile_notebook_id") else None),
    }


def _normalize_team_payload(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(existing or {})
    if "name" in payload or not base.get("name"):
        base["name"] = str(payload.get("name") or base.get("name") or "").strip()[:80] or "未命名战队"
    if "members" in payload:
        base["members"] = [_normalize_member(m) for m in (payload.get("members") or [])]
    else:
        base.setdefault("members", [])
    return base


def create_team(payload: dict[str, Any] | None = None, paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    now = datetime.now(timezone.utc).isoformat()
    team = _normalize_team_payload(payload or {})
    team.update({"schema_version": 1, "team_id": generate_team_id(paths), "created_at": now, "updated_at": now})
    return save_team(team, paths)


def save_team(team: dict[str, Any], paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    tid = normalize_team_id(team.get("team_id"))
    now = datetime.now(timezone.utc).isoformat()
    state = dict(team)
    state["team_id"] = tid
    state.setdefault("schema_version", 1)
    state.setdefault("created_at", now)
    state["updated_at"] = now
    state["members"] = [_normalize_member(m) for m in state.get("members", [])]
    teams_dir(paths).mkdir(parents=True, exist_ok=True)
    write_json_atomic(team_path(tid, paths), state)
    return state


def load_team(team_id: str, paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    path = team_path(team_id, paths)
    if not path.exists():
        raise KeyError(f"Unknown team_id: {team_id}")
    return read_json(path)


def update_team(team_id: str, payload: dict[str, Any], paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    existing = load_team(team_id, paths)
    merged = _normalize_team_payload(payload, existing)
    merged["team_id"] = existing["team_id"]
    merged["created_at"] = existing.get("created_at")
    return save_team(merged, paths)


def delete_team(team_id: str, paths: ProjectPaths | None = None) -> None:
    path = team_path(team_id, paths)
    if path.exists():
        path.unlink()


def list_teams(paths: ProjectPaths | None = None) -> list[dict[str, Any]]:
    paths = paths or project_paths()
    directory = teams_dir(paths)
    if not directory.exists():
        return []
    teams = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            team = read_json(path)
            tid = normalize_team_id(team.get("team_id") or path.stem)
        except Exception:
            continue
        teams.append(
            {
                "team_id": tid,
                "name": team.get("name") or "未命名战队",
                "member_count": len(team.get("members") or []),
                "created_at": team.get("created_at"),
                "updated_at": team.get("updated_at"),
            }
        )
    return teams


def save_sandbox_state(demo_id: str, payload: dict[str, Any], paths: ProjectPaths | None = None) -> dict[str, Any]:
    paths = paths or project_paths()
    resolve_demo_path(demo_id, paths)
    sandbox_dir = replay_cache_dir(demo_id, paths) / "sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state = dict(payload)
    state["demo_id"] = demo_id
    state.setdefault("source_match_id", demo_id)
    state.setdefault("source_round_number", state.get("round"))
    state.setdefault("source_tick", state.get("source_tick"))
    state.setdefault("created_at", state.get("created_at") or datetime.now(timezone.utc).isoformat())
    state.setdefault("objects", [])
    state.setdefault("notes", [])
    state.setdefault("token_positions", state.get("tokens", []))
    state.setdefault("arrows", [ann for ann in state.get("annotations", []) if ann.get("type") == "arrow"])
    state.setdefault("brush_strokes", [ann for ann in state.get("annotations", []) if ann.get("type") == "brush"])
    state.setdefault("planned_utilities", [])
    state.setdefault("schema_version", 1)
    state["saved_at"] = datetime.now(timezone.utc).isoformat()
    target = sandbox_dir / f"sandbox_{timestamp}.json"
    write_json(target, state)
    write_json(sandbox_dir / "latest.json", state)
    return {"saved": True, "path": str(target.relative_to(paths.root)), "latest": str((sandbox_dir / "latest.json").relative_to(paths.root)), "state": state}


def latest_sandbox_state(demo_id: str, paths: ProjectPaths | None = None) -> dict[str, Any] | None:
    paths = paths or project_paths()
    resolve_demo_path(demo_id, paths)
    latest = replay_cache_dir(demo_id, paths) / "sandbox" / "latest.json"
    if not latest.exists():
        return None
    return read_json(latest)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def clean_scalar(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return value


def clean_number(value: Any) -> float | None:
    value = clean_scalar(value)
    if value is None:
        return None
    number = to_float(value)
    if number is None or math.isnan(number) or math.isinf(number):
        return None
    return round(number, 3)


def clean_int(value: Any) -> int | None:
    value = clean_scalar(value)
    if value is None:
        return None
    return to_int(value)


def clean_bool(value: Any) -> bool | None:
    value = clean_scalar(value)
    if value is None:
        return None
    return bool(value)
