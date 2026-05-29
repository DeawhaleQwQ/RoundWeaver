from __future__ import annotations

import argparse
import logging
from pathlib import Path

from demoparser2 import DemoParser

from cs2demo.map_config import DEFAULT_OVERVIEW_PATH, DEFAULT_RADAR_PATH, load_dust2_config
from cs2demo.parser import Cs2DemoParser, P0_EVENTS, frame_to_records, write_outputs
from cs2demo.pipeline import ensure_analysis_outputs, parse_and_analyze
from cs2demo.renderer import render_kills_map
from cs2demo.replay import ensure_replay_cache, project_paths
from cs2demo.report import render_report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m cs2demo.cli", description="CS2 demo parser and Dust2 renderer")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser("parse", help="Parse a demo into outputs/*.json and tick samples")
    parse_cmd.add_argument("demo", type=Path)
    parse_cmd.add_argument("--out-dir", type=Path, default=Path("outputs"))
    parse_cmd.add_argument("--tick-interval", type=int, default=8)

    render_cmd = subparsers.add_parser("render-kills", help="Render all kill points on the Dust2 radar")
    render_cmd.add_argument("demo", type=Path)
    render_cmd.add_argument("--out", type=Path, default=Path("outputs/kills_map.png"))
    render_cmd.add_argument("--overview", type=Path, default=DEFAULT_OVERVIEW_PATH)
    render_cmd.add_argument("--radar", type=Path, default=DEFAULT_RADAR_PATH)

    analyze_cmd = subparsers.add_parser("analyze", help="Run deterministic Dust2 review rules and write findings")
    analyze_cmd.add_argument("demo", type=Path)
    analyze_cmd.add_argument("--out-dir", type=Path, default=Path("outputs"))
    analyze_cmd.add_argument("--tick-interval", type=int, default=8)
    analyze_cmd.add_argument("--tick-rate", type=float, default=64.0)
    analyze_cmd.add_argument("--scope", choices=["auto", "both", "T", "CT"], default="auto")

    report_cmd = subparsers.add_parser("report", help="Print a Chinese deterministic review report")
    report_cmd.add_argument("demo", type=Path)
    report_cmd.add_argument("--out-dir", type=Path, default=Path("outputs"))
    report_cmd.add_argument("--tick-interval", type=int, default=8)
    report_cmd.add_argument("--tick-rate", type=float, default=64.0)
    report_cmd.add_argument("--scope", choices=["auto", "both", "T", "CT"], default="auto")

    inspect_cmd = subparsers.add_parser("inspect-events", help="Print available demo events and utility event fields")
    inspect_cmd.add_argument("demo", type=Path)
    inspect_cmd.add_argument("--limit", type=int, default=3)

    export_cmd = subparsers.add_parser("export-replay", help="Build or refresh web replay cache")
    export_cmd.add_argument("demo", type=Path)
    export_cmd.add_argument("--demo-id", default=None)
    export_cmd.add_argument("--tick-interval", type=int, default=8)
    export_cmd.add_argument("--tick-rate", type=float, default=64.0)
    export_cmd.add_argument("--scope", choices=["auto", "both", "T", "CT"], default="auto")
    export_cmd.add_argument("--force", action="store_true", help="Rebuild replay cache from scratch")
    export_cmd.add_argument("--utility-trajectory-mode", choices=["auto", "precise", "approximate"], default="auto")

    map_cmd = subparsers.add_parser("map-info", help="Print parsed Dust2 overview config")
    map_cmd.add_argument("--overview", type=Path, default=DEFAULT_OVERVIEW_PATH)
    map_cmd.add_argument("--radar", type=Path, default=DEFAULT_RADAR_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s: %(message)s")
    logger = logging.getLogger("cs2demo")

    if args.command == "parse":
        parser = Cs2DemoParser(args.demo, logger=logger)
        result = parser.parse(tick_interval=args.tick_interval)
        write_outputs(result, args.out_dir)
        logger.info("Wrote summary to %s", args.out_dir / "summary.json")
        logger.info("Parsed map=%s players=%d rounds=%d events=%d tick_samples=%d", result.header.get("map_name"), len(result.players), len(result.rounds), len(result.events), len(result.tick_samples))
        return 0

    if args.command == "render-kills":
        render_kills_map(
            demo_path=args.demo,
            out_path=args.out,
            overview_path=args.overview,
            radar_path=args.radar,
            logger=logger,
        )
        return 0

    if args.command == "analyze":
        result = parse_and_analyze(args.demo, args.out_dir, args.tick_interval, args.tick_rate, args.scope, logger)
        logger.info("Wrote findings to %s", args.out_dir / "findings.json")
        logger.info("Wrote player metrics to %s", args.out_dir / "player_metrics.json")
        logger.info("Analysis finding counts: %s", result.metadata.get("finding_counts"))
        return 0

    if args.command == "report":
        ensure_analysis_outputs(args.demo, args.out_dir, args.tick_interval, args.tick_rate, args.scope, logger)
        print(render_report(args.out_dir), end="")
        return 0

    if args.command == "inspect-events":
        inspect_events(args.demo, args.limit)
        return 0

    if args.command == "export-replay":
        paths = project_paths()
        demo_id = args.demo_id or args.demo.stem
        manifest_path = ensure_replay_cache(demo_id, tick_interval=args.tick_interval, tick_rate=args.tick_rate, scope=args.scope, force=args.force, paths=paths, trajectory_mode=args.utility_trajectory_mode)
        logger.info("Wrote replay cache to %s", manifest_path)
        return 0

    if args.command == "map-info":
        cfg = load_dust2_config(args.overview, args.radar)
        logger.info("map_name=%s pos_x=%s pos_y=%s scale=%s radar=%s", cfg.map_name, cfg.pos_x, cfg.pos_y, cfg.scale, cfg.radar_path)
        return 0

    arg_parser.error(f"Unknown command: {args.command}")
    return 2


def inspect_events(demo: Path, limit: int = 3) -> None:
    parser = DemoParser(str(demo))
    events = sorted(parser.list_game_events())
    print(f"available_events={len(events)}")
    for event_name in events:
        print(event_name)

    wanted = sorted(set(P0_EVENTS) | {"grenade_thrown", "smokegrenade_expired", "inferno_expire", "decoy_detonate"})
    print("\nutility_event_samples:")
    for event_name in wanted:
        try:
            frame = parser.parse_event(event_name)
            records = frame_to_records(frame)
            columns = list(frame.columns) if hasattr(frame, "columns") else list(records[0].keys()) if records else []
            print(f"{event_name}: rows={len(records)} columns={columns}")
            for row in records[:limit]:
                print(f"  {row}")
        except Exception as exc:
            print(f"{event_name}: unavailable ({exc})")

    print("\ngrenade_projectiles:")
    try:
        frame = parser.parse_grenades()
        records = frame_to_records(frame)
        columns = list(frame.columns) if hasattr(frame, "columns") else list(records[0].keys()) if records else []
        print(f"parse_grenades: rows={len(records)} columns={columns}")
        counts: dict[str, int] = {}
        for row in records:
            grenade_type = str(row.get("grenade_type") or "unknown")
            counts[grenade_type] = counts.get(grenade_type, 0) + 1
        for grenade_type, count in sorted(counts.items()):
            print(f"  {grenade_type}: {count}")
        for row in records[:limit]:
            print(f"  {row}")
    except Exception as exc:
        print(f"parse_grenades: unavailable ({exc})")


if __name__ == "__main__":
    raise SystemExit(main())
