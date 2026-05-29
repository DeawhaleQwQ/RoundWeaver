from __future__ import annotations

from typing import Any

from cs2demo.analysis.engine import AnalysisContext, distance_2d, event_player_payload
from cs2demo.analysis.models import make_finding
from cs2demo.analysis.trade import find_trade_kill
from cs2demo.parser import to_int

ENTRY_SUCCESS_WINDOW_SEC = 15.0
ENTRY_FAIL_TRADE_WINDOW_SEC = 5.0
OBJECTIVE_PROGRESS_THRESHOLD = 450.0
TEAM_MOVEMENT_THRESHOLD = 500.0


def detect_entry_findings(ctx: AnalysisContext) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for round_row in ctx.rounds:
        round_number = to_int(round_row.get("round"))
        if round_number is None:
            continue
        contacts = sorted(ctx.events_in_window("player_death", round_number, to_int(round_row.get("start_tick")) or 0, to_int(round_row.get("end_tick")) or 0), key=lambda row: to_int(row.get("tick")) or -1)[:2]
        for index, contact in enumerate(contacts, start=1):
            tick = to_int(contact.get("tick"))
            attacker = contact.get("attacker_steamid")
            victim = contact.get("user_steamid")
            if tick is None or not attacker or not victim or attacker == victim:
                continue
            attacker_team = ctx.player_team(attacker, round_number, tick)
            victim_team = ctx.player_team(victim, round_number, tick)
            if not attacker_team or not victim_team or attacker_team == victim_team:
                continue

            if index == 1 and ctx.include_team(attacker_team):
                success = entry_success_evidence(ctx, round_number, attacker_team, tick)
                if success["is_success"]:
                    evidence = {
                        "round_number": round_number,
                        "contact_index": index,
                        "contact_tick": tick,
                        "contact_time_sec": ctx.round_time(round_number, tick),
                        "entry_player": event_player_payload(ctx, contact, "attacker_steamid", "attacker_name", "entry_player"),
                        "victim": event_player_payload(ctx, contact, "user_steamid", "user_name", "victim"),
                        "team": attacker_team,
                        "followup_window_sec": ENTRY_SUCCESS_WINDOW_SEC,
                        **success,
                    }
                    findings.append(
                        make_finding(
                            finding_id=f"entry_success-r{round_number}-t{tick}-{attacker}",
                            finding_type="entry_success",
                            title="突破成功",
                            sentiment="positive",
                            severity="info",
                            team=attacker_team,
                            round_number=round_number,
                            tick=tick,
                            players=[evidence["entry_player"], evidence["victim"]],
                            message=f"第 {round_number} 回合 {evidence['entry_player']['name']} 拿到首杀后，队伍在 15 秒内取得目标推进或完成下包。",
                            evidence=evidence,
                        )
                    )

            if index == 1 and ctx.include_team(victim_team):
                trade = find_trade_kill(ctx, round_number, victim_team, attacker, tick)
                if not trade:
                    evidence = {
                        "round_number": round_number,
                        "contact_index": index,
                        "contact_tick": tick,
                        "contact_time_sec": ctx.round_time(round_number, tick),
                        "entry_player": event_player_payload(ctx, contact, "user_steamid", "user_name", "entry_player"),
                        "killer": event_player_payload(ctx, contact, "attacker_steamid", "attacker_name", "killer"),
                        "team": victim_team,
                        "followup_window_sec": ENTRY_FAIL_TRADE_WINDOW_SEC,
                        "traded_within_5s": False,
                        "reason": "首死后 5 秒内无人击杀凶手",
                    }
                    findings.append(
                        make_finding(
                            finding_id=f"entry_failed_untraded-r{round_number}-t{tick}-{victim}",
                            finding_type="entry_failed_untraded",
                            title="突破失败且未补枪",
                            sentiment="negative",
                            severity="high",
                            team=victim_team,
                            round_number=round_number,
                            tick=tick,
                            players=[evidence["entry_player"], evidence["killer"]],
                            message=f"第 {round_number} 回合 {evidence['entry_player']['name']} 成为首死，5 秒内无人补枪。",
                            evidence=evidence,
                        )
                    )
    return findings


def entry_success_evidence(ctx: AnalysisContext, round_number: int, team: str, contact_tick: int) -> dict[str, Any]:
    end_tick = contact_tick + ctx.seconds_to_ticks(ENTRY_SUCCESS_WINDOW_SEC)
    plants = ctx.bomb_plants_in_window(team, round_number, contact_tick, end_tick)
    start_obj = ctx.objective_distance(team, round_number, contact_tick)
    end_obj = ctx.objective_distance(team, round_number, end_tick)
    site_progress_delta = None
    if start_obj is not None and end_obj is not None:
        site_progress_delta = round(start_obj - end_obj, 2)

    movement = average_team_movement(ctx, team, round_number, contact_tick, end_tick)
    plant_in_window = bool(plants)
    is_success = bool(
        plant_in_window
        or (site_progress_delta is not None and site_progress_delta >= OBJECTIVE_PROGRESS_THRESHOLD)
        or movement >= TEAM_MOVEMENT_THRESHOLD
    )
    reason = []
    if plant_in_window:
        reason.append("15 秒内完成下包")
    if site_progress_delta is not None and site_progress_delta >= OBJECTIVE_PROGRESS_THRESHOLD:
        reason.append("队伍明显接近包点")
    if movement >= TEAM_MOVEMENT_THRESHOLD:
        reason.append("队伍形成明显推进")
    return {
        "plant_in_window": plant_in_window,
        "plant_tick": to_int(plants[0].get("tick")) if plants else None,
        "site_progress_delta": site_progress_delta,
        "avg_team_movement": round(movement, 2),
        "traded_within_5s": None,
        "is_success": is_success,
        "reason": "；".join(reason) if reason else "未观察到足够后续推进",
    }


def average_team_movement(ctx: AnalysisContext, team: str, round_number: int, start_tick: int, end_tick: int) -> float:
    distances = []
    seen = {sample.get("steamid") for sample in ctx.samples_by_round_team.get((round_number, team), []) if sample.get("steamid")}
    for steamid in seen:
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
