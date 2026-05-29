from __future__ import annotations

from typing import Any

from cs2demo.analysis.engine import AnalysisContext, event_player_payload
from cs2demo.analysis.models import make_finding
from cs2demo.parser import to_int


def detect_postplant_findings(ctx: AnalysisContext) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for plant in sorted(ctx.events_by_type.get("bomb_planted", []), key=lambda row: to_int(row.get("tick")) or -1):
        round_number = to_int(plant.get("round"))
        plant_tick = to_int(plant.get("tick"))
        if round_number is None or plant_tick is None:
            continue
        round_row = ctx.rounds_by_number.get(round_number)
        if not round_row or round_row.get("winner_side") != "CT" or not ctx.include_team("T"):
            continue
        round_end_tick = to_int(round_row.get("end_tick")) or plant_tick
        defuses = ctx.events_in_window("bomb_defused", round_number, plant_tick, round_end_tick)
        deaths = postplant_death_order(ctx, round_number, plant_tick, round_end_tick)
        evidence = {
            "round_number": round_number,
            "plant_tick": plant_tick,
            "plant_time_sec": ctx.round_time(round_number, plant_tick),
            "site": plant.get("site"),
            "planter": event_player_payload(ctx, plant, "user_steamid", "user_name", "planter"),
            "post_plant_death_order": deaths,
            "defuser": event_player_payload(ctx, defuses[0], "user_steamid", "user_name", "defuser") if defuses else None,
            "defuse_tick": to_int(defuses[0].get("tick")) if defuses else None,
            "round_winner": round_row.get("winner_side"),
            "round_end_reason": round_row.get("reason"),
            "round_end_tick": round_end_tick,
        }
        findings.append(
            make_finding(
                finding_id=f"post_plant_lost-r{round_number}-t{plant_tick}",
                finding_type="post_plant_lost",
                title="包后失败",
                sentiment="negative",
                severity="high",
                team="T",
                round_number=round_number,
                tick=plant_tick,
                jump_tick=plant_tick,
                players=[evidence["planter"]] + ([evidence["defuser"]] if evidence["defuser"] else []),
                message=f"第 {round_number} 回合 T 方下包后最终被 CT 翻盘。",
                evidence=evidence,
            )
        )
    return findings


def postplant_death_order(ctx: AnalysisContext, round_number: int, plant_tick: int, round_end_tick: int) -> list[dict[str, Any]]:
    deaths = []
    for death in ctx.events_in_window("player_death", round_number, plant_tick, round_end_tick):
        victim = death.get("user_steamid")
        tick = to_int(death.get("tick"))
        if ctx.player_team(victim, round_number, tick) != "T":
            continue
        deaths.append(
            {
                "tick": tick,
                "time_after_plant_sec": round((tick - plant_tick) / ctx.tick_rate, 2) if tick is not None else None,
                "victim": event_player_payload(ctx, death, "user_steamid", "user_name", "victim"),
                "killer": event_player_payload(ctx, death, "attacker_steamid", "attacker_name", "killer"),
                "weapon": death.get("weapon"),
            }
        )
    return sorted(deaths, key=lambda row: row.get("tick") or -1)
