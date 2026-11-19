"""meshstress CLI.

  python -m meshstress suite  [-o reports/] [--obj-dir out/]   generate + check all
  python -m meshstress check  a.obj b.obj  [-o reports/]       check existing files
  python -m meshstress list
"""
from __future__ import annotations

import argparse
import sys
import time
import tracemalloc

from . import generators
from .checks import Limits, analyze
from .mesh import read_obj, write_obj
from .report import summary_markdown, write_reports


def run_check(mesh, limits: Limits, profile_mem: bool = False) -> dict:
    """Times the check. tracemalloc slows pure-Python code ~5-10x, so peak
    memory is measured in a separate pass only when asked for."""
    t0 = time.perf_counter()
    result = analyze(mesh, limits)
    result["timing_ms"] = (time.perf_counter() - t0) * 1000
    if profile_mem:
        tracemalloc.start()
        analyze(mesh, limits)
        result["peak_kib"] = tracemalloc.get_traced_memory()[1] / 1024
        tracemalloc.stop()
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="meshstress")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suite", help="generate every stress asset and check it")
    s.add_argument("-o", "--out", default="reports")
    s.add_argument("--obj-dir", help="also write generated OBJ files here")
    s.add_argument("--only", nargs="*", help="subset of generator names")
    c = sub.add_parser("check", help="check OBJ files")
    c.add_argument("files", nargs="+")
    c.add_argument("-o", "--out", default="reports")
    for p in (s, c):
        p.add_argument("--vram-mib", type=float, default=8.0)
        p.add_argument("--max-size-m", type=float, default=10.0)
        p.add_argument("--profile-mem", action="store_true",
                       help="also measure peak Python memory (slow)")
    sub.add_parser("list", help="list generators")
    a = ap.parse_args(argv)

    if a.cmd == "list":
        for name, fn in generators.ALL.items():
            kind = "clean " if name in generators.CLEAN else "broken"
            print(f"{kind}  {name:22} {(fn.__doc__ or '').strip().splitlines()[0]}")
        return 0

    limits = Limits(expected_size_m=(0.01, a.max_size_m),
                    vram_budget_bytes=int(a.vram_mib * 2**20))
    results = []
    if a.cmd == "suite":
        names = a.only or list(generators.ALL)
        for name in names:
            mesh = generators.ALL[name]()
            if a.obj_dir:
                write_obj(mesh, f"{a.obj_dir}/{name}.obj")
            r = run_check(mesh, limits, a.profile_mem)
            r["asset"] = name
            results.append(r)
    else:
        for f in a.files:
            results.append(run_check(read_obj(f), limits, a.profile_mem))
    write_reports(results, a.out)
    sys.stdout.write(summary_markdown(results))
    print(f"\nreports written to {a.out}/", file=sys.stderr)
    return 1 if a.cmd == "check" and any(r["status"] == "fail" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
