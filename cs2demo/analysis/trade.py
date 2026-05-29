from __future__ import annotations

from typing import Any

from cs2demo.analysis.engine import AnalysisContext, distance_2d, event_player_payload, player_payload
from cs2demo.analysis.models import make_finding
from cs2demo.parser import to_int

TRADE_WINDOW_SEC = 5.0
POSSIBLE_TRADE_DISTANCE = 900.0


def detect_trade_findings(ctx: AnalysisContext) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for death in sorted(ctx.events_by_type.get("player_death", []), key=lambda row: to_int(row.get("tick")) or -1):
        round_number = to_int(death.get("round"))
        death_tick = to_int(death.get("tick"))
        victim = death.get("user_steamid")
        killer = death.get("attacker_steamid")
        if round_number is None or death_tick is None or not victim or not killer or victim == killer:
            continue

        victim_team = ctx.player_team(victim, round_number, death_tick)
        killer_team = ctx.player_team(killer, round_number, death_tick)
        if not victim_team or not killer_team or victim_team == killer_team or not ctx.include_team(victim_team):
            continue

        trade = find_trade_kill(ctx, round_number, victim_team, killer, death_tick)
        victim_sample, victim_gap = ctx.position_for_event_player(death, "user_steamid")
        killer_sample = ctx.nearest_sample(killer, death_tick)
        nearest = nearest_teammate(ctx, victim_team, round_number, death_tick, {victim}, victim_sample, killer_sample.sample if killer_sample else None)
        distance_to_victim = nearest.get("distance_to_victim") if nearest else None
        distance_to_killer = nearest.get("distance_to_killer") if nearest else None
        possible_trade_missed = bool(
            not trade
            and nearest
            and (
                (distance_to_victim is not None and distance_to_victim < POSSIBLE_TRADE_DISTANCE)
                or (distance_to_killer is not None and distance_to_killer < POSSIBLE_TRADE_DISTANCE)
            )
        )

        evidence = {
            "round_number": round_number,
            "death_tick": death_tick,
            "death_time_sec": ctx.round_time(round_number, death_tick),
            "victim": event_player_payload(ctx, death, "user_steamid", "user_name", "victim"),
            "killer": event_player_payload(ctx, death, "attacker_steamid", "attacker_name", "killer"),
            "nearest_teammate": nearest.get("player") if nearest else None,
            "distance_to_victim": round(distance_to_victim, 2) if distance_to_victim is not None else None,
            "distance_to_killer": round(distance_to_killer, 2) if distance_to_killer is not None else None,
            "traded": trade is not None,
            "trade_delay_sec": trade.get("trade_delay_sec") if trade else None,
            "trade_kill": trade.get("kill") if trade else None,
            "possible_trade_missed": possible_trade_missed,
            "sample_tick": victim_sample.get("tick") if victim_sample else None,
            "sample_gap_ticks": victim_gap,
            "trade_window_sec": TRADE_WINDOW_SEC,
        }

        if trade:
            findings.append(
                make_finding(
                    finding_id=f"trade_success-r{round_number}-t{death_tick}-{victim}",
                    finding_type="trade_success",
                    title="成功补枪",
                    sentiment="positive",
                    severity="info",
                    team=victim_team,
                    round_number=round_number,
                    tick=death_tick,
                    players=[
                        evidence["victim"],
                        evidence["killer"],
                        player_payload(ctx, trade.get("trader_steamid"), "trader"),
                    ],
                    message=f"第 {round_number} 回合 {evidence['victim']['name']} 被击杀后，{ctx.player_name(trade.get('trader_steamid'))} 在 {trade['trade_delay_sec']} 秒内完成补枪。",
                    evidence=evidence,
                )
            )
        else:
            findings.append(
                make_finding(
                    finding_id=f"own_death_untraded-r{round_number}-t{death_tick}-{victim}",
                    finding_type="own_death_untraded",
                    title="没补上枪",
                    sentiment="negative",
                    severity="high" if possible_trade_missed else "medium",
                    team=victim_team,
                    round_number=round_number,
                    tick=death_tick,
                    players=[evidence["victim"], evidence["killer"]] + ([nearest["player"]] if nearest else []),
                    message=trade_fail_message(round_number, evidence, possible_trade_missed),
                    evidence=evidence,
                )
            )
    return findings


def find_trade_kill(ctx: AnalysisContext, round_number: int, victim_team: str, killer: str, death_tick: int) -> dict[str, Any] | None:
    end_tick = death_tick + ctx.seconds_to_ticks(TRADE_WINDOW_SEC)
    for kill in sorted(ctx.events_in_window("player_death", round_number, death_tick, end_tick), key=lambda row: to_int(row.get("tick")) or -1):
        if kill.get("user_steamid") != killer:
            continue
        trader = kill.get("attacker_steamid")
        if not trader or trader == killer:
            continue
        if ctx.player_team(trader, round_number, to_int(kill.get("tick"))) != victim_team:
            continue
        kill_tick = to_int(kill.get("tick")) or death_tick
        return {
            "trader_steamid": trader,
            "trade_tick": kill_tick,
            "trade_delay_sec": round((kill_tick - death_tick) / ctx.tick_rate, 2),
            "kill": kill,
        }
    return None


def nearest_teammate(
    ctx: AnalysisContext,
    team: str,
    round_number: int,
    death_tick: int,
    exclude_steamids: set[str],
    victim_sample: dict[str, Any] | None,
    killer_sample: dict[str, Any] | None,
) -> dict[str, Any] | None:
    candidates = []
    for teammate in ctx.alive_teammates(team, exclude_steamids, round_number, death_tick):
        distance_to_victim = distance_2d(teammate, victim_sample) if victim_sample else None
        distance_to_killer = distance_2d(teammate, killer_sample) if killer_sample else None
        rank_distance = min([d for d in (distance_to_victim, distance_to_killer) if d is not None], default=None)
        if rank_distance is None:
            continue
        candidates.append(
            {
                "player": {
                    "steamid": teammate.get("steamid"),
                    "name": teammate.get("name") or ctx.player_name(teammate.get("steamid")),
                    "team": team,
                    "role": "nearest_teammate",
                },
                "distance_to_victim": distance_to_victim,
                "distance_to_killer": distance_to_killer,
                "sample_tick": teammate.get("tick"),
            }
        )
    if not candidates:
        return None
    return min(candidates, key=lambda row: min([d for d in (row["distance_to_victim"], row["distance_to_killer"]) if d is not None]))


def trade_fail_message(round_number: int, evidence: dict[str, Any], possible_trade_missed: bool) -> str:
    victim = evidence["victim"]["name"]
    killer = evidence["killer"]["name"]
    nearest = evidence.get("nearest_teammate")
    if possible_trade_missed and nearest:
        return f"第 {round_number} 回合 {victim} 被 {killer} 击杀后 5 秒内无人补枪，最近队友 {nearest['name']} 距离较近，疑似可补枪未完成。"
    return f"第 {round_number} 回合 {victim} 被 {killer} 击杀后 5 秒内无人击杀凶手。"
