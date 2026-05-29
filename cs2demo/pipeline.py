from __future__ import annotations

from pathlib import Path
import logging

from cs2demo.analysis.analyzer import AnalysisResult, analyze_parse_result, write_analysis_outputs
from cs2demo.parser import Cs2DemoParser, P0_EVENTS, ParseResult, read_json, write_outputs


def parse_demo_outputs(
    demo: str | Path,
    out_dir: str | Path,
    tick_interval: int = 8,
    logger: logging.Logger | None = None,
) -> ParseResult:
    log = logger or logging.getLogger(__name__)
    parser = Cs2DemoParser(demo, logger=log)
    result = parser.parse(tick_interval=tick_interval)
    write_outputs(result, out_dir)
    return result


def parse_and_analyze(
    demo: str | Path,
    out_dir: str | Path,
    tick_interval: int = 8,
    tick_rate: float = 64.0,
    scope: str = "auto",
    logger: logging.Logger | None = None,
) -> AnalysisResult:
    result = parse_demo_outputs(demo, out_dir, tick_interval=tick_interval, logger=logger)
    analysis = analyze_parse_result(result, demo_path=demo, tick_rate=tick_rate, scope=scope)
    write_analysis_outputs(analysis, out_dir)
    return analysis


def ensure_analysis_outputs(
    demo: str | Path,
    out_dir: str | Path,
    tick_interval: int = 8,
    tick_rate: float = 64.0,
    scope: str = "auto",
    logger: logging.Logger | None = None,
) -> None:
    output_dir = Path(out_dir)
    required = [output_dir / "summary.json", output_dir / "findings.json", output_dir / "player_metrics.json"]
    ticks_present = (output_dir / "ticks.parquet").exists() or (output_dir / "ticks.csv").exists()
    if all(path.exists() for path in required) and ticks_present and events_are_current(output_dir):
        return
    log = logger or logging.getLogger(__name__)
    log.info("Analysis outputs not found or stale; running parse/analyze first")
    parse_and_analyze(demo, output_dir, tick_interval=tick_interval, tick_rate=tick_rate, scope=scope, logger=log)


def events_are_current(output_dir: Path) -> bool:
    summary_path = output_dir / "summary.json"
    if not summary_path.exists():
        return False
    try:
        summary = read_json(summary_path)
    except Exception:
        return False
    counts = summary.get("key_events", {}).get("event_counts", {})
    return all(name in counts for name in P0_EVENTS)
