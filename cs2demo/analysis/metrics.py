from __future__ import annotations

from collections import defaultdict
from typing import Any


METRIC_ZEROES = {
    "own_death_untraded_count": 0,
    "possible_trade_missed_count": 0,
    "trade_success_count": 0,
    "entry_success_count": 0,
    "entry_failed_untraded_count": 0,
    "low_value_stall_count": 0,
    "post_plant_lost_count": 0,
}


def build_player_metrics(player_stats: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, dict[str, Any]] = {}
    for stat in player_stats:
        steamid = stat.get("steamid")
        if not steamid:
            continue
        row = dict(stat)
        row.update(METRIC_ZEROES)
        metrics[steamid] = row

    for finding in findings:
        finding_type = finding.get("finding_type")
        evidence = finding.get("evidence", {})
        if finding_type == "own_death_untraded":
            victim = evidence.get("victim", {}).get("steamid")
            add(metrics, victim, "own_death_untraded_count")
            if evidence.get("possible_trade_missed"):
                add(metrics, victim, "possible_trade_missed_count")
                teammate = evidence.get("nearest_teammate", {}).get("steamid") if evidence.get("nearest_teammate") else None
                add(metrics, teammate, "possible_trade_missed_count")
        elif finding_type == "trade_success":
            trader = find_role(finding, "trader")
            add(metrics, trader, "trade_success_count")
        elif finding_type == "entry_success":
            player = evidence.get("entry_player", {}).get("steamid")
            add(metrics, player, "entry_success_count")
        elif finding_type == "entry_failed_untraded":
            player = evidence.get("entry_player", {}).get("steamid")
            add(metrics, player, "entry_failed_untraded_count")
        elif finding_type == "low_value_stall_window":
            for player in finding.get("players", []):
                add(metrics, player.get("steamid"), "low_value_stall_count")
        elif finding_type == "post_plant_lost":
            planter = evidence.get("planter", {}).get("steamid")
            add(metrics, planter, "post_plant_lost_count")
            for death in evidence.get("post_plant_death_order", []):
                add(metrics, death.get("victim", {}).get("steamid"), "post_plant_lost_count")

    teams: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in metrics.values():
        deaths = row.get("deaths") or 0
        entry_attempts = row["entry_success_count"] + row["entry_failed_untraded_count"]
        row["own_death_untraded_rate"] = round(row["own_death_untraded_count"] / deaths, 3) if deaths else 0.0
        row["entry_success_rate"] = round(row["entry_success_count"] / entry_attempts, 3) if entry_attempts else 0.0
        row["entry_attempts"] = entry_attempts
        teams[row.get("team") or "UNKNOWN"].append(row)

    output = {}
    for team, rows in teams.items():
        output[team] = {
            "summary": summarize_team(rows),
            "players": sorted(rows, key=lambda item: item.get("name") or ""),
        }
    return output


def add(metrics: dict[str, dict[str, Any]], steamid: str | None, key: str) -> None:
    if not steamid:
        return
    if steamid not in metrics:
        row = {"steamid": steamid, "name": steamid, "team": None}
        row.update(METRIC_ZEROES)
        metrics[steamid] = row
    metrics[steamid][key] += 1


def find_role(finding: dict[str, Any], role: str) -> str | None:
    for player in finding.get("players", []):
        if player.get("role") == role:
            return player.get("steamid")
    return None


def summarize_team(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "players": len(rows),
        "kills": sum(row.get("kills") or 0 for row in rows),
        "deaths": sum(row.get("deaths") or 0 for row in rows),
        "own_death_untraded_count": sum(row.get("own_death_untraded_count") or 0 for row in rows),
        "possible_trade_missed_count": sum(row.get("possible_trade_missed_count") or 0 for row in rows),
        "entry_success_count": sum(row.get("entry_success_count") or 0 for row in rows),
        "entry_failed_untraded_count": sum(row.get("entry_failed_untraded_count") or 0 for row in rows),
        "low_value_stall_count": sum(row.get("low_value_stall_count") or 0 for row in rows),
        "post_plant_lost_count": sum(row.get("post_plant_lost_count") or 0 for row in rows),
    }
