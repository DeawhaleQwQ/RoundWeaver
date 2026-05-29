from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_player_stats(
    players: list[dict[str, Any]],
    kills: list[dict[str, Any]],
    damages: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    names: dict[str, str] = {}
    teams: dict[str, str | None] = {}
    for player in players:
        steamid = player.get("steamid")
        if not steamid:
            continue
        names[steamid] = player.get("name") or steamid
        teams[steamid] = player.get("team")

    stats: dict[str, dict[str, Any]] = defaultdict(new_stats)
    for steamid, name in names.items():
        stats[steamid]["steamid"] = steamid
        stats[steamid]["name"] = name
        stats[steamid]["team"] = teams.get(steamid)

    first_kill_by_round: set[int] = set()
    round_count = max(len(rounds), 1)

    for kill in kills:
        attacker = kill.get("attacker_steamid")
        victim = kill.get("user_steamid")
        assister = kill.get("assister_steamid")
        round_number = kill.get("round")

        if attacker and attacker != victim:
            ensure_player(stats, attacker, kill.get("attacker_name"), names, teams)
            stats[attacker]["kills"] += 1
            if kill.get("headshot"):
                stats[attacker]["headshots"] += 1
            is_first_kill = round_number not in first_kill_by_round
            if is_first_kill:
                stats[attacker]["first_kills"] += 1
                first_kill_by_round.add(round_number)
        else:
            is_first_kill = round_number not in first_kill_by_round

        if victim:
            ensure_player(stats, victim, kill.get("user_name"), names, teams)
            stats[victim]["deaths"] += 1
            if is_first_kill:
                stats[victim]["first_deaths"] += 1

        if assister:
            ensure_player(stats, assister, kill.get("assister_name"), names, teams)
            stats[assister]["assists"] += 1

    for damage in damages:
        attacker = damage.get("attacker_steamid")
        victim = damage.get("user_steamid")
        if not attacker or attacker == victim:
            continue
        ensure_player(stats, attacker, damage.get("attacker_name"), names, teams)
        stats[attacker]["damage"] += int(damage.get("dmg_health") or 0)

    output = []
    for row in stats.values():
        kills_count = row["kills"]
        row["adr"] = round(row["damage"] / round_count, 2)
        row["hs_percent"] = round((row["headshots"] / kills_count) * 100, 2) if kills_count else 0.0
        output.append(dict(row))
    return sorted(output, key=lambda item: (item.get("team") or "", item.get("name") or ""))


def new_stats() -> dict[str, Any]:
    return {
        "steamid": None,
        "name": None,
        "team": None,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "damage": 0,
        "adr": 0.0,
        "headshots": 0,
        "hs_percent": 0.0,
        "first_kills": 0,
        "first_deaths": 0,
    }


def ensure_player(
    stats: dict[str, dict[str, Any]],
    steamid: str,
    name: Any,
    names: dict[str, str],
    teams: dict[str, str | None],
) -> None:
    stats[steamid]["steamid"] = steamid
    stats[steamid]["name"] = name or names.get(steamid) or steamid
    stats[steamid]["team"] = teams.get(steamid)
