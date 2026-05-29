from __future__ import annotations

from typing import Any


def make_player(steamid: str | None, name: str | None, team: str | None, role: str) -> dict[str, Any]:
    return {
        "steamid": steamid,
        "name": name,
        "team": team,
        "role": role,
    }


def make_finding(
    finding_id: str,
    finding_type: str,
    title: str,
    sentiment: str,
    severity: str,
    team: str | None,
    round_number: int | None,
    tick: int | None,
    players: list[dict[str, Any]],
    message: str,
    evidence: dict[str, Any],
    jump_tick: int | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "finding_type": finding_type,
        "title": title,
        "sentiment": sentiment,
        "severity": severity,
        "team": team,
        "round_number": round_number,
        "tick": tick,
        "jump_tick": jump_tick if jump_tick is not None else tick,
        "players": players,
        "message": message,
        "evidence": evidence,
    }
