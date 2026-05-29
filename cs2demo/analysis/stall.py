from __future__ import annotations

from typing import Any

from cs2demo.analysis.engine import AnalysisContext, distance_2d
from cs2demo.analysis.models import make_finding
from cs2demo.parser import to_int

STALL_WINDOW_SEC = 15.0
STALL_STEP_SEC = 5.0
MAX_STALLS_PER_ROUND_TEAM = 2
MOVEMENT_THRESHOLD = 260.0
OBJECTIVE_PROGRESS_THRESHOLD = 180.0


def detect_stall_findings(ctx: AnalysisContext) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for round_row in ctx.rounds:
        round_number = to_int(round_row.get("round"))
        if round_number is None:
            continue
        start_tick = to_int(round_row.get("freeze_end_tick")) or to_int(round_row.get("start_tick"))
        end_tick = to_int(round_row.get("end_tick"))
        if start_tick is None or end_tick is None:
            continue
        for team in ("T", "CT"):
            if not ctx.include_team(team):
                continue
            windows = stall_windows_for_team(ctx, round_number, team, start_tick, end_tick)
            for idx, evidence in enumerate(windows[:MAX_STALLS_PER_ROUND_TEAM], start=1):
                findings.append(
                    make_finding(
                        finding_id=f"low_value_stall_window-r{round_number}-{team}-{idx}-{evidence['start_tick']}",
                        finding_type="low_value_stall_window",
                        title="便秘回合 / 低价值停滞",
                        sentiment="negative",
                        severity="medium",
                        team=team,
                        round_number=round_number,
                        tick=evidence["start_tick"],
                        jump_tick=evidence["start_tick"],
                        players=team_players_in_window(ctx, team, round_number, evidence["start_tick"], evidence["end_tick"]),
                        message=f"第 {round_number} 回合 {team} 方在 {evidence['start_time']}s-{evidence['end_time']}s 出现低价值停滞。",
                        evidence=evidence,
                    )
                )
    return findings


def stall_windows_for_team(ctx: AnalysisContext, round_number: int, team: str, round_start: int, round_end: int) -> list[dict[str, Any]]:
    window_ticks = ctx.seconds_to_ticks(STALL_WINDOW_SEC)
    step_ticks = ctx.seconds_to_ticks(STALL_STEP_SEC)
    if round_end - round_start < window_ticks:
        return []
    candidates = []
    tick = round_start
    while tick + window_ticks <= round_end:
        evidence = evaluate_window(ctx, round_number, team, tick, tick + window_ticks)
        if is_low_value(evidence):
            candidates.append(evidence)
        tick += step_ticks
    return merge_adjacent(candidates, ctx)


def evaluate_window(ctx: AnalysisContext, round_number: int, team: str, start_tick: int, end_tick: int) -> dict[str, Any]:
    kills = ctx.team_kills_in_window(team, round_number, start_tick, end_tick)
    damages = ctx.team_damage_in_window(team, round_number, start_tick, end_tick)
    utility = ctx.team_utility_in_window(team, round_number, start_tick, end_tick)
    plants = ctx.bomb_plants_in_window(team, round_number, start_tick, end_tick)
    avg_movement = average_movement(ctx, team, round_number, start_tick, end_tick)
    objective_start = ctx.objective_distance(team, round_number, start_tick)
    objective_end = ctx.objective_distance(team, round_number, end_tick)
    objective_progress = None
    if objective_start is not None and objective_end is not None:
        objective_progress = round(objective_start - objective_end, 2)
    return {
        "round_number": round_number,
        "start_time": ctx.round_time(round_number, start_tick),
        "end_time": ctx.round_time(round_number, end_tick),
        "team": team,
        "avg_movement": round(avg_movement, 2),
        "damage_count": len(damages),
        "kill_count": len(kills),
        "utility_count": len(utility),
        "plant_count": len(plants),
        "objective_progress": objective_progress,
        "reason": "窗口内无击杀/有效伤害/下包/有效道具，且移动和目标推进低于阈值",
        "start_tick": start_tick,
        "end_tick": end_tick,
        "thresholds": {
            "movement": MOVEMENT_THRESHOLD,
            "objective_progress": OBJECTIVE_PROGRESS_THRESHOLD,
            "window_sec": STALL_WINDOW_SEC,
        },
    }


def is_low_value(evidence: dict[str, Any]) -> bool:
    objective_progress = evidence.get("objective_progress")
    if objective_progress is None:
        objective_progress = 0.0
    return (
        evidence["kill_count"] == 0
        and evidence["damage_count"] == 0
        and evidence["utility_count"] == 0
        and evidence["plant_count"] == 0
        and evidence["avg_movement"] < MOVEMENT_THRESHOLD
        and objective_progress < OBJECTIVE_PROGRESS_THRESHOLD
    )


def average_movement(ctx: AnalysisContext, team: str, round_number: int, start_tick: int, end_tick: int) -> float:
    distances = []
    steamids = {sample.get("steamid") for sample in ctx.samples_by_round_team.get((round_number, team), []) if sample.get("steamid")}
    for steamid in steamids:
        start = ctx.nearest_sample(steamid, start_tick)
        end = ctx.nearest_sample(steamid, end_tick)
        if not start or not end:
            continue
        distance = distance_2d(start.sample, end.sample)
        if distance is not None:
            distances.append(distance)
    if not distances:
        return 0.0
    return sum(distances) / len(distances)


def merge_adjacent(windows: list[dict[str, Any]], ctx: AnalysisContext) -> list[dict[str, Any]]:
    if not windows:
        return []
    merged = [dict(windows[0])]
    for window in windows[1:]:
        current = merged[-1]
        if window["start_tick"] <= current["end_tick"]:
            current["end_tick"] = max(current["end_tick"], window["end_tick"])
            current["end_time"] = ctx.round_time(current["round_number"], current["end_tick"])
            current["avg_movement"] = round(min(current["avg_movement"], window["avg_movement"]), 2)
            current["damage_count"] += window["damage_count"]
            current["kill_count"] += window["kill_count"]
            current["utility_count"] += window["utility_count"]
        else:
            merged.append(dict(window))
    return sorted(merged, key=lambda row: (row["kill_count"] + row["damage_count"] + row["utility_count"], row["avg_movement"]))


def team_players_in_window(ctx: AnalysisContext, team: str, round_number: int, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
    players = []
    seen: set[str] = set()
    for sample in ctx.samples_by_round_team.get((round_number, team), []):
        tick = to_int(sample.get("tick"))
        steamid = sample.get("steamid")
        if steamid in seen or tick is None or tick < start_tick or tick > end_tick:
            continue
        seen.add(steamid)
        players.append({"steamid": steamid, "name": sample.get("name") or ctx.player_name(steamid), "team": team, "role": "participant"})
    return players
