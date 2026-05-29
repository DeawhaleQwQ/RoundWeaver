from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
import json

ROUND_WEIGHTS = {
    "post_plant_lost": 5,
    "own_death_untraded": 4,
    "entry_failed_untraded": 3,
    "low_value_stall_window": 2,
    "entry_success": 1,
    "trade_success": 1,
}


def load_report_data(out_dir: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = Path(out_dir)
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    findings = json.loads((base / "findings.json").read_text(encoding="utf-8"))
    metrics = json.loads((base / "player_metrics.json").read_text(encoding="utf-8"))
    return summary, findings, metrics


def render_report(out_dir: str | Path) -> str:
    summary, findings_payload, metrics_payload = load_report_data(out_dir)
    findings = findings_payload.get("findings", [])
    lines: list[str] = []
    lines.extend(section_overview(summary, findings_payload))
    lines.extend(section_player_stats(metrics_payload))
    lines.extend(section_top_rounds(findings))
    lines.extend(section_trade(findings))
    lines.extend(section_entry(findings))
    lines.extend(section_stall(findings))
    lines.extend(section_postplant(findings))
    return "\n".join(lines).rstrip() + "\n"


def section_overview(summary: dict[str, Any], findings_payload: dict[str, Any]) -> list[str]:
    header = summary.get("match_header", {})
    metadata = findings_payload.get("metadata", {})
    counts = metadata.get("finding_counts", {})
    lines = [
        "# Dust2 Demo 规则复盘报告",
        "",
        "## 比赛概览",
        f"- 地图：{header.get('map_name')}",
        f"- 玩家数：{len(summary.get('players', []))}",
        f"- 回合数：{len(summary.get('rounds', []))}",
        f"- 分析范围：{metadata.get('scope')}（未配置我方 roster 时默认按 T/CT 双方输出）",
        f"- Finding 总数：{sum(counts.values())}",
        f"- 主要问题计数：没补枪 {counts.get('own_death_untraded', 0)}，突破失败 {counts.get('entry_failed_untraded', 0)}，便秘窗口 {counts.get('low_value_stall_window', 0)}，包后失败 {counts.get('post_plant_lost', 0)}",
        "",
    ]
    return lines


def section_player_stats(metrics_payload: dict[str, Any]) -> list[str]:
    lines = ["## 每个人基础数据", ""]
    teams = metrics_payload.get("teams", {})
    for team in sorted(teams):
        lines.append(f"### {team} 方")
        for row in teams[team].get("players", []):
            lines.append(
                f"- {row.get('name')}：K/D/A {row.get('kills')}/{row.get('deaths')}/{row.get('assists')}，"
                f"ADR {row.get('adr')}，HS% {row.get('hs_percent')}，"
                f"未补枪死亡 {row.get('own_death_untraded_count')}，疑似漏补 {row.get('possible_trade_missed_count')}，"
                f"突破成功 {row.get('entry_success_count')}，突破失败 {row.get('entry_failed_untraded_count')}"
            )
        lines.append("")
    return lines


def section_top_rounds(findings: list[dict[str, Any]]) -> list[str]:
    round_scores: dict[int, dict[str, Any]] = defaultdict(lambda: {"score": 0, "types": defaultdict(int)})
    for finding in findings:
        round_number = finding.get("round_number")
        if round_number is None:
            continue
        weight = ROUND_WEIGHTS.get(finding.get("finding_type"), 0)
        if finding.get("evidence", {}).get("possible_trade_missed"):
            weight += 1
        round_scores[int(round_number)]["score"] += weight
        round_scores[int(round_number)]["types"][finding.get("finding_type")] += 1
    ranked = sorted(round_scores.items(), key=lambda item: item[1]["score"], reverse=True)[:5]
    lines = ["## 最值得复盘的 5 个回合", ""]
    if not ranked:
        lines.append("- 暂无足够 finding 用于排序。")
        lines.append("")
        return lines
    for round_number, payload in ranked:
        type_text = "，".join(f"{label_finding_type(key)} x{value}" for key, value in payload["types"].items())
        lines.append(f"- 第 {round_number} 回合：复盘分 {payload['score']}，{type_text}")
    lines.append("")
    return lines


def section_trade(findings: list[dict[str, Any]]) -> list[str]:
    rows = [finding for finding in findings if finding.get("finding_type") == "own_death_untraded"]
    lines = ["## 没补枪问题", ""]
    if not rows:
        lines.append("- 未发现未补枪 finding。")
        lines.append("")
        return lines
    for finding in rows[:12]:
        ev = finding["evidence"]
        nearest = ev.get("nearest_teammate") or {}
        lines.append(
            f"- R{ev.get('round_number')} {ev.get('death_time_sec')}s：{ev.get('victim', {}).get('name')} 被 {ev.get('killer', {}).get('name')} 击杀，"
            f"5 秒内未补枪；最近队友 {nearest.get('name') or '无'}，距死者 {format_value(ev.get('distance_to_victim'))}，距凶手 {format_value(ev.get('distance_to_killer'))}，"
            f"疑似漏补：{yes_no(ev.get('possible_trade_missed'))}。"
        )
    lines.append("")
    return lines


def section_entry(findings: list[dict[str, Any]]) -> list[str]:
    successes = [finding for finding in findings if finding.get("finding_type") == "entry_success"]
    failures = [finding for finding in findings if finding.get("finding_type") == "entry_failed_untraded"]
    lines = ["## 突破成功回合", ""]
    if successes:
        for finding in successes[:10]:
            ev = finding["evidence"]
            lines.append(f"- R{ev.get('round_number')} {ev.get('contact_time_sec')}s：{ev.get('entry_player', {}).get('name')} 为 {ev.get('team')} 方拿到首杀，后续：{ev.get('reason')}。")
    else:
        lines.append("- 未发现突破成功 finding。")
    lines.extend(["", "## 突破失败回合", ""])
    if failures:
        for finding in failures[:10]:
            ev = finding["evidence"]
            lines.append(f"- R{ev.get('round_number')} {ev.get('contact_time_sec')}s：{ev.get('entry_player', {}).get('name')} 首死，{ev.get('reason')}。")
    else:
        lines.append("- 未发现突破失败 finding。")
    lines.append("")
    return lines


def section_stall(findings: list[dict[str, Any]]) -> list[str]:
    rows = [finding for finding in findings if finding.get("finding_type") == "low_value_stall_window"]
    lines = ["## 便秘回合", ""]
    if not rows:
        lines.append("- 未发现低价值停滞窗口。")
        lines.append("")
        return lines
    for finding in rows[:12]:
        ev = finding["evidence"]
        lines.append(
            f"- R{ev.get('round_number')} {ev.get('team')} 方 {ev.get('start_time')}s-{ev.get('end_time')}s："
            f"平均移动 {ev.get('avg_movement')}，伤害 {ev.get('damage_count')}，击杀 {ev.get('kill_count')}，道具 {ev.get('utility_count')}；{ev.get('reason')}。"
        )
    lines.append("")
    return lines


def section_postplant(findings: list[dict[str, Any]]) -> list[str]:
    rows = [finding for finding in findings if finding.get("finding_type") == "post_plant_lost"]
    lines = ["## 包后失败回合", ""]
    if not rows:
        lines.append("- 未发现包后失败 finding。")
        lines.append("")
        return lines
    for finding in rows:
        ev = finding["evidence"]
        defuser = ev.get("defuser") or {}
        deaths = " -> ".join(death.get("victim", {}).get("name") or "未知" for death in ev.get("post_plant_death_order", [])) or "无 T 方死亡记录"
        lines.append(
            f"- R{ev.get('round_number')}：{ev.get('planter', {}).get('name')} 在点位 {ev.get('site')} 下包，最终 CT 获胜；"
            f"拆包者 {defuser.get('name')}，T 方死亡顺序：{deaths}，原因：{ev.get('round_end_reason')}。"
        )
    lines.append("")
    return lines


def label_finding_type(finding_type: str) -> str:
    labels = {
        "own_death_untraded": "没补枪",
        "trade_success": "成功补枪",
        "entry_success": "突破成功",
        "entry_failed_untraded": "突破失败",
        "low_value_stall_window": "便秘窗口",
        "post_plant_lost": "包后失败",
    }
    return labels.get(finding_type, finding_type)


def format_value(value: Any) -> str:
    return "无" if value is None else str(value)


def yes_no(value: Any) -> str:
    return "是" if value else "否"
