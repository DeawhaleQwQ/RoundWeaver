from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Any

from cs2demo.parser import ParseResult, to_float, to_int

BOMB_SITES = {
    "A": (1175.0, 2490.0, 95.0),
    "B": (-1700.0, 2520.0, 8.0),
}

UTILITY_EVENTS = {
    "player_blind",
    "hegrenade_detonate",
    "smokegrenade_detonate",
    "flashbang_detonate",
    "inferno_startburn",
}


@dataclass(frozen=True)
class SampleLookup:
    sample: dict[str, Any]
    gap_ticks: int


class AnalysisContext:
    def __init__(self, result: ParseResult, tick_rate: float = 64.0, scope: str = "auto") -> None:
        self.result = result
        self.header = result.header
        self.players = result.players
        self.rounds = result.rounds
        self.events_by_type = result.events_by_type
        self.tick_samples = result.tick_samples
        self.player_stats = result.player_stats
        self.tick_rate = tick_rate
        self.scope = self.resolve_scope(scope)

        self.players_by_steamid = {player.get("steamid"): player for player in self.players if player.get("steamid")}
        self.rounds_by_number = {to_int(row.get("round")): row for row in self.rounds if to_int(row.get("round")) is not None}
        self.samples_by_steamid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.samples_by_round_team: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)

        for sample in self.tick_samples:
            steamid = sample.get("steamid")
            round_number = to_int(sample.get("round"))
            team = sample.get("team")
            if steamid:
                self.samples_by_steamid[steamid].append(sample)
            if round_number is not None and team:
                self.samples_by_round_team[(round_number, team)].append(sample)

        self.sample_ticks_by_steamid: dict[str, list[int]] = {}
        for steamid, samples in self.samples_by_steamid.items():
            samples.sort(key=lambda row: to_int(row.get("tick")) or -1)
            self.sample_ticks_by_steamid[steamid] = [to_int(row.get("tick")) or -1 for row in samples]

        for samples in self.samples_by_round_team.values():
            samples.sort(key=lambda row: (to_int(row.get("tick")) or -1, row.get("steamid") or ""))

    def resolve_scope(self, scope: str) -> str:
        if scope == "auto":
            return "both"
        return scope

    def include_team(self, team: str | None) -> bool:
        if not team:
            return False
        return self.scope in {"both", team}

    def seconds_to_ticks(self, seconds: float) -> int:
        return int(round(seconds * self.tick_rate))

    def ticks_to_seconds(self, ticks: int | float | None) -> float | None:
        if ticks is None:
            return None
        return round(float(ticks) / self.tick_rate, 2)

    def round_time(self, round_number: int | None, tick: int | None) -> float | None:
        if round_number is None or tick is None:
            return None
        round_row = self.rounds_by_number.get(round_number)
        if not round_row:
            return None
        start_tick = to_int(round_row.get("freeze_end_tick")) or to_int(round_row.get("start_tick"))
        if start_tick is None:
            return None
        return self.ticks_to_seconds(max(0, tick - start_tick))

    def player_name(self, steamid: str | None) -> str | None:
        if not steamid:
            return None
        player = self.players_by_steamid.get(steamid)
        if player:
            return player.get("name")
        for event_rows in self.events_by_type.values():
            for event in event_rows:
                if event.get("user_steamid") == steamid:
                    return event.get("user_name")
                if event.get("attacker_steamid") == steamid:
                    return event.get("attacker_name")
        return steamid

    def player_team(self, steamid: str | None, round_number: int | None = None, tick: int | None = None) -> str | None:
        if not steamid:
            return None
        if tick is not None:
            sample_lookup = self.nearest_sample(steamid, tick)
            if sample_lookup and sample_lookup.sample.get("team"):
                return sample_lookup.sample.get("team")
        player = self.players_by_steamid.get(steamid)
        if player and player.get("team"):
            return player.get("team")
        return None

    def nearest_sample(self, steamid: str | None, tick: int | None, max_gap_ticks: int | None = None) -> SampleLookup | None:
        if not steamid or tick is None:
            return None
        samples = self.samples_by_steamid.get(steamid, [])
        ticks = self.sample_ticks_by_steamid.get(steamid, [])
        if not samples or not ticks:
            return None
        pos = bisect_left(ticks, tick)
        candidates = []
        if pos < len(samples):
            candidates.append(samples[pos])
        if pos > 0:
            candidates.append(samples[pos - 1])
        best = min(candidates, key=lambda row: abs((to_int(row.get("tick")) or 0) - tick))
        gap = abs((to_int(best.get("tick")) or 0) - tick)
        if max_gap_ticks is not None and gap > max_gap_ticks:
            return None
        return SampleLookup(best, gap)

    def position_for_event_player(self, event: dict[str, Any], steamid_field: str) -> tuple[dict[str, Any] | None, int | None]:
        tick = to_int(event.get("tick"))
        steamid = event.get(steamid_field)
        lookup = self.nearest_sample(steamid, tick)
        if lookup:
            return lookup.sample, lookup.gap_ticks
        if all(event.get(key) is not None for key in ("x", "y")):
            return {
                "steamid": steamid,
                "name": self.player_name(steamid),
                "team": self.player_team(steamid, tick=tick),
                "tick": tick,
                "X": event.get("x"),
                "Y": event.get("y"),
                "Z": event.get("z"),
                "is_alive": None,
            }, 0
        return None, None

    def alive_teammates(self, team: str, exclude_steamids: set[str], round_number: int, tick: int) -> list[dict[str, Any]]:
        by_player: dict[str, dict[str, Any]] = {}
        for sample in self.samples_by_round_team.get((round_number, team), []):
            steamid = sample.get("steamid")
            if not steamid or steamid in exclude_steamids:
                continue
            sample_tick = to_int(sample.get("tick"))
            if sample_tick is None:
                continue
            existing = by_player.get(steamid)
            if existing is None or abs(sample_tick - tick) < abs((to_int(existing.get("tick")) or 0) - tick):
                by_player[steamid] = sample
        teammates = []
        for sample in by_player.values():
            if sample.get("is_alive") is False:
                continue
            teammates.append(sample)
        return teammates

    def events_in_window(self, event_name: str, round_number: int, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        return [
            event for event in self.events_by_type.get(event_name, [])
            if to_int(event.get("round")) == round_number
            and to_int(event.get("tick")) is not None
            and start_tick <= int(event["tick"]) <= end_tick
        ]

    def team_kills_in_window(self, team: str, round_number: int, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        output = []
        for event in self.events_in_window("player_death", round_number, start_tick, end_tick):
            attacker = event.get("attacker_steamid")
            victim = event.get("user_steamid")
            if attacker and attacker != victim and self.player_team(attacker, round_number, to_int(event.get("tick"))) == team:
                output.append(event)
        return output

    def team_damage_in_window(self, team: str, round_number: int, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        output = []
        for event in self.events_in_window("player_hurt", round_number, start_tick, end_tick):
            attacker = event.get("attacker_steamid")
            victim = event.get("user_steamid")
            if not attacker or attacker == victim:
                continue
            if self.player_team(attacker, round_number, to_int(event.get("tick"))) == team and (to_int(event.get("dmg_health")) or 0) > 0:
                output.append(event)
        return output

    def team_utility_in_window(self, team: str, round_number: int, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        output = []
        for event_name in UTILITY_EVENTS:
            for event in self.events_in_window(event_name, round_number, start_tick, end_tick):
                actor = event.get("user_steamid") or event.get("attacker_steamid")
                if self.player_team(actor, round_number, to_int(event.get("tick"))) == team:
                    output.append(event)
        return output

    def bomb_plants_in_window(self, team: str, round_number: int, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        if team != "T":
            return []
        return self.events_in_window("bomb_planted", round_number, start_tick, end_tick)

    def team_average_position(self, team: str, round_number: int, tick: int) -> tuple[float, float] | None:
        samples = []
        for steamid, player in self.players_by_steamid.items():
            if self.player_team(steamid, round_number, tick) != team:
                continue
            lookup = self.nearest_sample(steamid, tick)
            if lookup and lookup.sample.get("is_alive") is not False:
                x = to_float(lookup.sample.get("X"))
                y = to_float(lookup.sample.get("Y"))
                if x is not None and y is not None:
                    samples.append((x, y))
        if not samples:
            return None
        return (sum(x for x, _ in samples) / len(samples), sum(y for _, y in samples) / len(samples))

    def objective_distance(self, team: str, round_number: int, tick: int) -> float | None:
        avg = self.team_average_position(team, round_number, tick)
        if not avg:
            return None
        if team == "T":
            return min(distance_2d(avg, BOMB_SITES["A"]), distance_2d(avg, BOMB_SITES["B"]))
        return None


def distance_2d(a: dict[str, Any] | tuple[float, float] | tuple[float, float, float], b: dict[str, Any] | tuple[float, float] | tuple[float, float, float]) -> float | None:
    ax, ay = xy(a)
    bx, by = xy(b)
    if ax is None or ay is None or bx is None or by is None:
        return None
    return sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def xy(value: dict[str, Any] | tuple[float, ...]) -> tuple[float | None, float | None]:
    if isinstance(value, dict):
        return to_float(value.get("X") if value.get("X") is not None else value.get("x")), to_float(value.get("Y") if value.get("Y") is not None else value.get("y"))
    if len(value) >= 2:
        return to_float(value[0]), to_float(value[1])
    return None, None


def player_payload(ctx: AnalysisContext, steamid: str | None, role: str) -> dict[str, Any]:
    return {
        "steamid": steamid,
        "name": ctx.player_name(steamid),
        "team": ctx.player_team(steamid),
        "role": role,
    }


def event_player_payload(ctx: AnalysisContext, event: dict[str, Any], steamid_field: str, name_field: str, role: str) -> dict[str, Any]:
    steamid = event.get(steamid_field)
    return {
        "steamid": steamid,
        "name": event.get(name_field) or ctx.player_name(steamid),
        "team": ctx.player_team(steamid, to_int(event.get("round")), to_int(event.get("tick"))),
        "role": role,
    }
