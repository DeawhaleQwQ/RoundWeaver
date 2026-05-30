from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from demoparser2 import DemoParser

EVENTS_TO_INSPECT = [
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
    "flashbang_detonate",
    "inferno_startburn",
    "weapon_fire",
]

TICK_PROP_CANDIDATES = [
    "X",
    "Y",
    "Z",
    "eye_yaw",
    "yaw",
    "health",
    "armor_value",
    "is_alive",
    "life_state",
    "active_weapon_name",
    "has_bomb",
    "team_name",
    "team_num",
    "player_name",
    "steamid",
    "balance",
    "current_equip_value",
    "inventory",
    "cash_spent_this_round",
    "total_cash_spent",
]


def columns_of(frame: Any) -> list[str]:
    cols = getattr(frame, "columns", [])
    return list(cols) if cols is not None else []


def height_of(frame: Any) -> int:
    if hasattr(frame, "height"):
        return int(frame.height)
    if hasattr(frame, "shape"):
        return int(frame.shape[0])
    return 0


def preview_rows(frame: Any, limit: int = 3) -> list[dict[str, Any]]:
    if height_of(frame) == 0:
        return []
    if hasattr(frame, "head"):
        sample = frame.head(limit)
    else:
        sample = frame
    if hasattr(sample, "to_dicts"):
        return sample.to_dicts()
    if hasattr(sample, "to_dict"):
        return sample.to_dict(orient="records")
    return []


def print_frame_info(title: str, frame: Any) -> None:
    print(f"\n## {title}")
    print(f"rows={height_of(frame)}")
    print(f"columns={columns_of(frame)}")
    rows = preview_rows(frame)
    if rows:
        print("sample_rows=")
        for row in rows:
            print(row)


def main() -> int:
    arg_parser = argparse.ArgumentParser(description="Inspect demoparser2 fields for a CS2 demo.")
    arg_parser.add_argument("demo", type=Path)
    args = arg_parser.parse_args()

    if not args.demo.exists():
        raise FileNotFoundError(args.demo)

    parser = DemoParser(str(args.demo))

    header = parser.parse_header()
    print("## header")
    print(type(header).__name__)
    if isinstance(header, dict):
        print(f"keys={sorted(header.keys())}")
        for key in sorted(header.keys()):
            print(f"{key}={header[key]!r}")
    else:
        print(header)

    try:
        game_events = parser.list_game_events()
        print("\n## list_game_events")
        print(game_events)
    except Exception as exc:
        print(f"\n## list_game_events failed: {exc}")

    try:
        fields = parser.list_updated_fields()
        print("\n## list_updated_fields")
        if isinstance(fields, list):
            print(f"count={len(fields)}")
            print(fields[:200])
        else:
            print(fields)
    except Exception as exc:
        print(f"\n## list_updated_fields failed: {exc}")
        fields = []

    try:
        player_info = parser.parse_player_info()
        print_frame_info("parse_player_info", player_info)
    except Exception as exc:
        print(f"\n## parse_player_info failed: {exc}")

    round_ticks: list[int] = []
    for event_name in EVENTS_TO_INSPECT:
        try:
            event_frame = parser.parse_event(event_name)
        except Exception as exc:
            print(f"\n## event {event_name} failed: {exc}")
            continue
        print_frame_info(f"event {event_name}", event_frame)
        if event_name == "round_start" and height_of(event_frame) > 0:
            for row in preview_rows(event_frame, 10):
                tick = row.get("tick") or row.get("game_time_tick")
                if tick is not None:
                    round_ticks.append(int(tick))

    available_props = [prop for prop in TICK_PROP_CANDIDATES if not fields or prop in fields]
    if not available_props:
        available_props = TICK_PROP_CANDIDATES[:6]

    tick_filter = sorted(set(round_ticks[:2])) or None
    try:
        tick_frame = parser.parse_ticks(available_props, ticks=tick_filter)
        print_frame_info(f"parse_ticks props={available_props} ticks={tick_filter}", tick_frame)
    except Exception as exc:
        print(f"\n## parse_ticks failed with props={available_props}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
