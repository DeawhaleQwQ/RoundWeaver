from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import logging
import math

from demoparser2 import DemoParser

from cs2demo.analysis.basic_stats import build_player_stats

SUPPORTED_MAP = "de_dust2"

P0_EVENTS = [
    "player_death",
    "player_hurt",
    "bomb_planted",
    "bomb_defused",
    "bomb_exploded",
    "round_start",
    "round_freeze_end",
    "round_end",
    "player_blind",
    "hegrenade_detonate",
    "smokegrenade_detonate",
    "smokegrenade_expired",
    "flashbang_detonate",
    "inferno_startburn",
    "inferno_expire",
    "decoy_detonate",
    "weapon_fire",
]

TICK_PROPS = [
    "X",
    "Y",
    "Z",
    "yaw",
    "health",
    "armor_value",
    "is_alive",
    "active_weapon_name",
    "has_bomb",
    "team_name",
    "team_num",
    "balance",
    "current_equip_value",
    "inventory",
    "cash_spent_this_round",
]

POSITION_PROPS = ["X", "Y", "Z"]
STEAMID_FIELDS = ("steamid", "user_steamid", "attacker_steamid", "assister_steamid")


@dataclass
class ParseResult:
    header: dict[str, Any]
    players: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    events_by_type: dict[str, list[dict[str, Any]]]
    events: list[dict[str, Any]]
    tick_samples: list[dict[str, Any]]
    player_stats: list[dict[str, Any]]
    summary: dict[str, Any]


class Cs2DemoParser:
    def __init__(self, demo_path: str | Path, logger: logging.Logger | None = None) -> None:
        self.demo_path = Path(demo_path)
        if not self.demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {self.demo_path}")
        self.logger = logger or logging.getLogger(__name__)
        self.parser = DemoParser(str(self.demo_path))

    def parse(self, tick_interval: int = 8) -> ParseResult:
        self.logger.info("Reading demo header: %s", self.demo_path)
        header = clean_record(dict(self.parser.parse_header()))
        map_name = header.get("map_name")
        self.logger.info("Demo map_name=%s", map_name)
        if map_name != SUPPORTED_MAP:
            raise ValueError(f"Only {SUPPORTED_MAP} is supported, got {map_name!r}")

        players = self.parse_players()
        self.logger.info("Parsed %d players", len(players))

        events_by_type = self.parse_events()
        rounds = build_rounds(events_by_type)
        self.logger.info("Built %d rounds", len(rounds))

        for records in events_by_type.values():
            assign_rounds(records, rounds)

        if events_by_type.get("player_death"):
            self.enrich_events_with_positions(events_by_type["player_death"], "user_steamid")
        for event_name in ("bomb_planted", "bomb_defused", "bomb_exploded"):
            if events_by_type.get(event_name):
                self.enrich_events_with_positions(events_by_type[event_name], "user_steamid")

        events = sorted(
            [event for records in events_by_type.values() for event in records],
            key=lambda row: (row.get("tick") if row.get("tick") is not None else -1, row.get("event_type") or ""),
        )
        self.logger.info("Parsed %d total key/P0 events", len(events))

        tick_samples = self.parse_tick_samples(rounds, tick_interval=tick_interval)
        self.logger.info("Parsed %d player tick samples", len(tick_samples))

        player_stats = build_player_stats(
            players=players,
            kills=events_by_type.get("player_death", []),
            damages=events_by_type.get("player_hurt", []),
            rounds=rounds,
        )
        summary = build_summary(header, players, rounds, player_stats, events_by_type)

        return ParseResult(
            header=header,
            players=players,
            rounds=rounds,
            events_by_type=events_by_type,
            events=events,
            tick_samples=tick_samples,
            player_stats=player_stats,
            summary=summary,
        )

    def parse_kills_for_render(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        header = clean_record(dict(self.parser.parse_header()))
        map_name = header.get("map_name")
        self.logger.info("Demo map_name=%s", map_name)
        if map_name != SUPPORTED_MAP:
            raise ValueError(f"Only {SUPPORTED_MAP} is supported, got {map_name!r}")
        kills = self.parse_event_records("player_death")
        self.enrich_events_with_positions(kills, "user_steamid")
        self.logger.info("Parsed %d kill events for rendering", len(kills))
        return header, kills

    def parse_players(self) -> list[dict[str, Any]]:
        frame = self.parser.parse_player_info()
        players: list[dict[str, Any]] = []
        for row in frame_to_records(frame):
            record = clean_record(row)
            steamid = stringify_id(record.get("steamid"))
            team_number = to_int(record.get("team_number"))
            players.append(
                {
                    "steamid": steamid,
                    "name": record.get("name"),
                    "team_number": team_number,
                    "team": normalize_team(team_num=team_number),
                }
            )
        return players

    def parse_events(self) -> dict[str, list[dict[str, Any]]]:
        events_by_type: dict[str, list[dict[str, Any]]] = {}
        for event_name in P0_EVENTS:
            try:
                records = self.parse_event_records(event_name)
            except Exception as exc:
                self.logger.warning("Failed to parse event %s: %s", event_name, exc)
                records = []
            events_by_type[event_name] = records
            self.logger.info("Parsed event %-24s %d rows", event_name, len(records))
        return events_by_type

    def parse_event_records(self, event_name: str) -> list[dict[str, Any]]:
        frame = self.parser.parse_event(event_name)
        records: list[dict[str, Any]] = []
        for row in frame_to_records(frame):
            record = clean_record(row)
            record["event_type"] = event_name
            stringify_steamids(record)
            if "tick" in record:
                record["tick"] = to_int(record.get("tick"))
            records.append(record)
        return records

    def enrich_events_with_positions(self, records: list[dict[str, Any]], steamid_field: str) -> None:
        wanted = [row for row in records if row.get("tick") is not None and row.get(steamid_field)]
        ticks = sorted({int(row["tick"]) for row in wanted})
        if not ticks:
            return

        try:
            frame = self.parser.parse_ticks(POSITION_PROPS, ticks=ticks)
        except Exception as exc:
            self.logger.warning("Could not enrich event positions: %s", exc)
            return

        positions: dict[tuple[int, str], dict[str, Any]] = {}
        for row in frame_to_records(frame):
            record = clean_record(row)
            tick = to_int(record.get("tick"))
            steamid = stringify_id(record.get("steamid"))
            if tick is None or not steamid:
                continue
            positions[(tick, steamid)] = record

        missing = 0
        for event in wanted:
            key = (int(event["tick"]), stringify_id(event.get(steamid_field)))
            position = positions.get(key)
            if not position:
                missing += 1
                continue
            event.setdefault("x", position.get("X"))
            event.setdefault("y", position.get("Y"))
            event.setdefault("z", position.get("Z"))
        if missing:
            self.logger.info("Position enrichment missed %d/%d events", missing, len(wanted))

    def parse_tick_samples(self, rounds: list[dict[str, Any]], tick_interval: int = 8) -> list[dict[str, Any]]:
        if tick_interval <= 0:
            raise ValueError("tick_interval must be > 0")
        ticks = sampled_ticks(rounds, tick_interval)
        if not ticks:
            self.logger.warning("No rounds available for tick sampling")
            return []

        self.logger.info("Parsing %d sampled ticks with interval=%d", len(ticks), tick_interval)
        frame = self.parser.parse_ticks(TICK_PROPS, ticks=ticks)
        samples: list[dict[str, Any]] = []
        for row in frame_to_records(frame):
            record = clean_record(row)
            tick = to_int(record.get("tick"))
            team = normalize_team(record.get("team_name"), record.get("team_num"))
            steamid = stringify_id(record.get("steamid"))
            alive = record.get("is_alive")
            if alive is None and record.get("life_state") is not None:
                alive = to_int(record.get("life_state")) == 0
            inventory = record.get("inventory")
            if isinstance(inventory, (list, tuple)):
                weapons = [str(item) for item in inventory if item is not None]
            else:
                weapons = []
            samples.append(
                {
                    "tick": tick,
                    "round": find_round_for_tick(tick, rounds) if tick is not None else None,
                    "name": record.get("name"),
                    "steamid": steamid,
                    "team": team,
                    "side": team,
                    "X": to_float(record.get("X")),
                    "Y": to_float(record.get("Y")),
                    "Z": to_float(record.get("Z")),
                    "yaw": to_float(record.get("yaw")),
                    "health": to_int(record.get("health")),
                    "armor": to_int(record.get("armor_value")),
                    "is_alive": bool(alive) if alive is not None else None,
                    "active_weapon_name": record.get("active_weapon_name"),
                    "has_bomb": record.get("has_bomb"),
                    "balance": to_int(record.get("balance")),
                    "equip_value": to_int(record.get("current_equip_value")),
                    "weapons": weapons,
                    "cash_spent": to_int(record.get("cash_spent_this_round")),
                }
            )
        return samples


def parse_demo(demo_path: str | Path, output_dir: str | Path = "outputs", tick_interval: int = 8) -> ParseResult:
    parser = Cs2DemoParser(demo_path)
    result = parser.parse(tick_interval=tick_interval)
    write_outputs(result, output_dir)
    return result


def write_outputs(result: ParseResult, output_dir: str | Path) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    write_json(out_dir / "header.json", result.header)
    write_json(out_dir / "players.json", result.players)
    write_json(out_dir / "rounds.json", result.rounds)
    write_json(out_dir / "summary.json", result.summary)
    write_jsonl(out_dir / "events.jsonl", result.events)

    try:
        import pandas as pd

        ticks_path = out_dir / "ticks.parquet"
        pd.DataFrame(result.tick_samples).to_parquet(ticks_path, index=False)
    except Exception:
        import pandas as pd

        ticks_path = out_dir / "ticks.csv"
        pd.DataFrame(result.tick_samples).to_csv(ticks_path, index=False)


def build_summary(
    header: dict[str, Any],
    players: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
    player_stats: list[dict[str, Any]],
    events_by_type: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    bomb_events = []
    for name in ("bomb_planted", "bomb_defused", "bomb_exploded"):
        bomb_events.extend(events_by_type.get(name, []))
    return {
        "match_header": header,
        "players": players,
        "rounds": rounds,
        "player_stats": player_stats,
        "key_events": {
            "kills": events_by_type.get("player_death", []),
            "damages": events_by_type.get("player_hurt", []),
            "bomb": sorted(bomb_events, key=lambda row: row.get("tick") or -1),
            "event_counts": {name: len(records) for name, records in events_by_type.items()},
        },
    }


def build_rounds(events_by_type: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    starts = sorted(events_by_type.get("round_start", []), key=lambda row: row.get("tick") or -1)
    freeze_ticks = sorted(to_int(row.get("tick")) for row in events_by_type.get("round_freeze_end", []) if row.get("tick") is not None)
    ends = sorted(events_by_type.get("round_end", []), key=lambda row: row.get("tick") or -1)

    rounds: list[dict[str, Any]] = []
    previous_end = -1
    for end in ends:
        round_number = to_int(end.get("round"))
        end_tick = to_int(end.get("tick"))
        if not round_number or round_number <= 0 or end_tick is None:
            continue

        matching_starts = [
            row for row in starts
            if to_int(row.get("round")) == round_number
            and row.get("tick") is not None
            and previous_end < int(row["tick"]) <= end_tick
        ]
        if not matching_starts:
            matching_starts = [
                row for row in starts
                if row.get("tick") is not None and previous_end < int(row["tick"]) <= end_tick
            ]
        start_tick = max((to_int(row.get("tick")) for row in matching_starts), default=previous_end + 1)
        freeze_end_tick = next((tick for tick in freeze_ticks if start_tick is not None and start_tick <= tick <= end_tick), None)

        rounds.append(
            {
                "round": round_number,
                "start_tick": start_tick,
                "freeze_end_tick": freeze_end_tick,
                "end_tick": end_tick,
                "winner_side": end.get("winner"),
                "reason": end.get("reason"),
            }
        )
        previous_end = end_tick
    return rounds


def assign_rounds(records: list[dict[str, Any]], rounds: list[dict[str, Any]]) -> None:
    for record in records:
        tick = to_int(record.get("tick"))
        existing = to_int(record.get("round"))
        if existing and existing > 0:
            record["round"] = existing
        elif tick is not None:
            record["round"] = find_round_for_tick(tick, rounds)
        else:
            record["round"] = None


def sampled_ticks(rounds: list[dict[str, Any]], tick_interval: int) -> list[int]:
    ticks: set[int] = set()
    for round_row in rounds:
        start = to_int(round_row.get("start_tick"))
        end = to_int(round_row.get("end_tick"))
        if start is None or end is None or end < start:
            continue
        ticks.update(range(start, end + 1, tick_interval))
        ticks.add(end)
        if round_row.get("freeze_end_tick") is not None:
            ticks.add(int(round_row["freeze_end_tick"]))
    return sorted(ticks)


def find_round_for_tick(tick: int | None, rounds: list[dict[str, Any]]) -> int | None:
    if tick is None:
        return None
    for round_row in rounds:
        start = to_int(round_row.get("start_tick"))
        end = to_int(round_row.get("end_tick"))
        if start is not None and end is not None and start <= tick <= end:
            return to_int(round_row.get("round"))
    return None


def frame_to_records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if hasattr(frame, "to_dicts"):
        return list(frame.to_dicts())
    if hasattr(frame, "to_dict"):
        return list(frame.to_dict(orient="records"))
    return []


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: clean_value(value) for key, value in record.items()}


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    return value


def stringify_steamids(record: dict[str, Any]) -> None:
    for field in STEAMID_FIELDS:
        if field in record:
            record[field] = stringify_id(record.get(field))


def stringify_id(value: Any) -> str | None:
    value = clean_value(value)
    if value is None or value == "":
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def normalize_team(team_name: Any = None, team_num: Any = None) -> str | None:
    if team_name:
        value = str(team_name).upper()
        if value in {"T", "TERRORIST", "TERRORISTS"}:
            return "T"
        if value in {"CT", "COUNTERTERRORIST", "COUNTER_TERRORIST", "COUNTER-TERRORIST"}:
            return "CT"
        return str(team_name)
    number = to_int(team_num)
    if number == 2:
        return "T"
    if number == 3:
        return "CT"
    return None


def to_int(value: Any) -> int | None:
    value = clean_value(value)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    value = clean_value(value)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False))
            handle.write("\n")
