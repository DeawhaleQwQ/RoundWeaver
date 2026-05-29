from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cs2demo.analysis.engine import AnalysisContext
from cs2demo.analysis.entry import detect_entry_findings
from cs2demo.analysis.metrics import build_player_metrics
from cs2demo.analysis.postplant import detect_postplant_findings
from cs2demo.analysis.stall import detect_stall_findings
from cs2demo.analysis.trade import detect_trade_findings
from cs2demo.parser import ParseResult, write_json

ANALYSIS_VERSION = "0.2.0"


@dataclass
class AnalysisResult:
    metadata: dict[str, Any]
    findings: list[dict[str, Any]]
    player_metrics: dict[str, Any]


def analyze_parse_result(
    result: ParseResult,
    demo_path: str | Path,
    tick_rate: float = 64.0,
    scope: str = "auto",
) -> AnalysisResult:
    ctx = AnalysisContext(result, tick_rate=tick_rate, scope=scope)
    findings = []
    findings.extend(detect_trade_findings(ctx))
    findings.extend(detect_entry_findings(ctx))
    findings.extend(detect_stall_findings(ctx))
    findings.extend(detect_postplant_findings(ctx))
    findings.sort(key=lambda row: (row.get("round_number") or 0, row.get("tick") or 0, row.get("finding_type") or ""))

    metadata = {
        "analysis_version": ANALYSIS_VERSION,
        "demo_path": str(demo_path),
        "map_name": result.header.get("map_name"),
        "tick_rate": tick_rate,
        "scope": ctx.scope,
        "scope_note": "config/players.yaml 为空时默认按 T/CT 双方分析" if ctx.scope == "both" else None,
        "finding_counts": count_findings(findings),
    }
    player_metrics = {
        "metadata": metadata,
        "teams": build_player_metrics(result.player_stats, findings),
    }
    return AnalysisResult(
        metadata=metadata,
        findings=findings,
        player_metrics=player_metrics,
    )


def write_analysis_outputs(analysis: AnalysisResult, output_dir: str | Path) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "findings.json", {"metadata": analysis.metadata, "findings": analysis.findings})
    write_json(out_dir / "player_metrics.json", analysis.player_metrics)


def count_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        key = finding.get("finding_type") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts
