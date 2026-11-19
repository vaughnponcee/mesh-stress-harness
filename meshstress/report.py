"""JSON and Markdown diagnostic reports."""
from __future__ import annotations

import json
from pathlib import Path


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    return str(v)


def to_markdown(result: dict) -> str:
    out = [f"# {result['asset']}: {result['status'].upper()}", ""]
    out += ["| stat | value |", "|---|---|"]
    out += [f"| {k} | {_fmt(v)} |" for k, v in result["stats"].items()]
    out += [""]
    if result["findings"]:
        out += ["| severity | check | count | detail |", "|---|---|---:|---|"]
        for f in result["findings"]:
            out.append(f"| {f['severity']} | {f['check']} | {f['count'] or ''} | {f['message']} |")
    else:
        out.append("No findings.")
    if "timing_ms" in result:
        line = f"Check time: {result['timing_ms']:.1f} ms"
        if "peak_kib" in result:
            line += f", peak Python memory: {result['peak_kib']:.0f} KiB"
        out += ["", line]
    return "\n".join(out) + "\n"


def summary_markdown(results: list[dict]) -> str:
    out = ["# Mesh stress-test summary", "",
           "| asset | status | tris | VRAM KiB | errors | warnings | ms |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for r in results:
        e = sum(f["severity"] == "error" for f in r["findings"])
        w = sum(f["severity"] == "warn" for f in r["findings"])
        out.append(f"| {r['asset']} | {r['status']} | {r['stats'].get('triangles', 0)} | "
                   f"{r['stats'].get('vram_bytes', 0) / 1024:.1f} | {e} | {w} | "
                   f"{r.get('timing_ms', 0):.1f} |")
    return "\n".join(out) + "\n"


def write_reports(results: list[dict], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for r in results:
        (out / f"{r['asset']}.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
        (out / f"{r['asset']}.md").write_text(to_markdown(r), encoding="utf-8")
    (out / "SUMMARY.md").write_text(summary_markdown(results), encoding="utf-8")
    return out
