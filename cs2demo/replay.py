from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import math
import shutil

import pandas as pd
from PIL import Image

from cs2demo.analysis.utility import build_utility_events_bounded, load_utility_effect_config, summarize_utility_events, utility_markers
from cs2demo.map_config import DEFAULT_OVERVIEW_PATH, DEFAULT_RADAR_PATH, load_dust2_config
from cs2demo.parser import to_float, to_int, write_json
from cs2demo.pipeline import ensure_analysis_outputs

REPLAY_VERSION = "0.6.0"
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
]


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


def read_ticks(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path, columns=TICK_COLUMNS)
    else:
        frame = pd.read_csv(path, usecols=TICK_COLUMNS)
    return normalize_ticks_frame(frame)


def read_round_ticks(path: Path, round_number: int) -> pd.DataFrame:
    if path.suffix == ".parquet":
        try:
            frame = pd.read_parquet(path, columns=TICK_COLUMNS, filters=[("round", "==", round_number)])
        except Exception:
            frame = pd.read_parquet(path, columns=TICK_COLUMNS)
            frame = frame[frame["round"] == round_number]
        return normalize_ticks_frame(frame)

    chunks = []
    for chunk in pd.read_csv(path, usecols=TICK_COLUMNS, chunksize=250_000):
        chunk = chunk[chunk["round"] == round_number]
        if not chunk.empty:
            chunks.append(chunk)
    if not chunks:
        return pd.DataFrame(columns=TICK_COLUMNS)
    return normalize_ticks_frame(pd.concat(chunks, ignore_index=True))


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
            radar_x, radar_y = map_cfg.game_to_radar(float(row_data["X"]), float(row_data["Y"]))
            players.append(
                {
                    "steamid": str(row_data["steamid"]),
                    "name": clean_scalar(row_data.get("name")),
                    "team": clean_scalar(row_data.get("team")),
                    "side": clean_scalar(row_data.get("side")),
                    "x": clean_number(row_data.get("X")),
                    "y": clean_number(row_data.get("Y")),
                    "z": clean_number(row_data.get("Z")),
                    "radar_x": round(radar_x, 2),
                    "radar_y": round(radar_y, 2),
                    "yaw": clean_number(row_data.get("yaw")),
                    "health": clean_int(row_data.get("health")),
                    "armor": clean_int(row_data.get("armor")),
                    "is_alive": bool(row_data.get("is_alive")),
                    "active_weapon_name": clean_scalar(row_data.get("active_weapon_name")),
                    "has_bomb": bool(row_data.get("has_bomb")) if row_data.get("has_bomb") is not None and not pd.isna(row_data.get("has_bomb")) else None,
                }
            )
        frames.append({"tick": int(tick), "players": players})
    return frames


def round_manifest(rounds: list[dict[str, Any]], ticks: pd.DataFrame, demo_id: str) -> list[dict[str, Any]]:
    frame_counts = ticks.groupby("round")["tick"].nunique().to_dict()
    return round_manifest_from_counts(rounds, {int(key): int(value) for key, value in frame_counts.items()}, demo_id)


def round_manifest_from_counts(rounds: list[dict[str, Any]], frame_counts: dict[int, int], demo_id: str) -> list[dict[str, Any]]:
    return [
        {
            **round_row,
            "frame_count": int(frame_counts.get(to_int(round_row.get("round")) or -1, 0)),
            "round_url": f"/api/demos/{demo_id}/rounds/{round_row.get('round')}",
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
