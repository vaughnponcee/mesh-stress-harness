"""Mesh diagnostics. Pure Python; O(F) except duplicate-vertex hashing."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from .mesh import Mesh

AREA_EPS = 1e-12          # m^2 -- below this a triangle is degenerate
SLIVER_ASPECT = 50.0      # longest edge^2 / (2*area) ... high = needle/sliver
SHARP_DIHEDRAL_DEG = 60.0
THIN_RATIO = 0.005        # min extent / max extent
VERTEX_STRIDE = 32        # bytes: float3 position + float3 normal + float2 uv


@dataclass
class Limits:
    expected_size_m: tuple[float, float] = (0.01, 10.0)  # plausible largest extent
    vram_budget_bytes: int = 8 * 1024 * 1024             # per-asset, low-end mobile tier
    max_com_offset: float = 0.2                           # fraction of extent, worst axis
    min_bend_radius_m: float = 0.005                      # smooth surfaces tighter than this


@dataclass
class Finding:
    check: str
    severity: str  # error | warn | info
    message: str
    count: int = 0
    samples: list = field(default_factory=list)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a):
    return math.sqrt(_dot(a, a))


def analyze(mesh: Mesh, limits: Limits | None = None) -> dict:
    limits = limits or Limits()
    V, tris = mesh.verts, mesh.triangles()
    findings: list[Finding] = []
    stats: dict = {"vertices": len(V), "faces": len(mesh.faces), "triangles": len(tris)}

    if not V or not tris:
        findings.append(Finding("empty", "error", "mesh has no geometry"))
        return _result(mesh, stats, findings)

    bad_index = [i for i, t in enumerate(tris) if any(not 0 <= k < len(V) for k in t)]
    if bad_index:
        findings.append(Finding("index_out_of_range", "error",
                                "face references a vertex that does not exist",
                                len(bad_index), bad_index[:5]))
        return _result(mesh, stats, findings)

    # --- per-triangle geometry -------------------------------------------
    degenerate, slivers = [], []
    normals: list[tuple | None] = []
    area_total = 0.0
    vol6 = 0.0
    com = [0.0, 0.0, 0.0]
    min_edge, max_edge = math.inf, 0.0
    for ti, (a, b, c) in enumerate(tris):
        pa, pb, pc = V[a], V[b], V[c]
        n = _cross(_sub(pb, pa), _sub(pc, pa))
        area2 = _len(n)
        e = [_len(_sub(pb, pa)), _len(_sub(pc, pb)), _len(_sub(pa, pc))]
        if a == b or b == c or a == c or area2 * 0.5 < AREA_EPS:
            degenerate.append(ti)
            normals.append(None)
            continue
        min_edge, max_edge = min(min_edge, *e), max(max_edge, *e)
        area_total += area2 * 0.5
        normals.append((n[0] / area2, n[1] / area2, n[2] / area2))
        if max(e) ** 2 / area2 > SLIVER_ASPECT:
            slivers.append(ti)
        # signed tetra volume against origin (divergence theorem)
        v = _dot(pa, _cross(pb, pc))
        vol6 += v
        for k in range(3):
            com[k] += v * (pa[k] + pb[k] + pc[k])
    stats["surface_area_m2"] = area_total
    stats["min_edge_m"] = min_edge if min_edge < math.inf else 0.0
    stats["max_edge_m"] = max_edge

    if degenerate:
        findings.append(Finding("degenerate_triangles", "error",
                                "zero-area or collapsed triangles", len(degenerate), degenerate[:5]))
    if slivers:
        sev = "warn" if len(slivers) / len(tris) > 0.01 else "info"
        findings.append(Finding("sliver_triangles", sev,
                                f"needle/sliver triangles (aspect > {SLIVER_ASPECT:g})",
                                len(slivers), slivers[:5]))

    # --- topology -----------------------------------------------------------
    edge_faces: dict[tuple[int, int], list[int]] = {}
    directed = Counter()
    for ti, (a, b, c) in enumerate(tris):
        if normals[ti] is None:
            continue
        for u, v in ((a, b), (b, c), (c, a)):
            edge_faces.setdefault((min(u, v), max(u, v)), []).append(ti)
            directed[(u, v)] += 1
    nonmanifold = [e for e, fs in edge_faces.items() if len(fs) > 2]
    boundary = [e for e, fs in edge_faces.items() if len(fs) == 1]
    flipped = [e for e in edge_faces if len(edge_faces[e]) == 2
               and (directed[e] == 2 or directed[(e[1], e[0])] == 2)]
    stats["edges"] = len(edge_faces)
    if nonmanifold:
        findings.append(Finding("non_manifold_edges", "error",
                                "edges shared by more than two faces", len(nonmanifold),
                                [list(e) for e in nonmanifold[:5]]))
    if boundary:
        findings.append(Finding("boundary_edges", "warn",
                                "open edges: mesh is not watertight", len(boundary),
                                [list(e) for e in boundary[:5]]))
    if flipped:
        findings.append(Finding("inconsistent_winding", "warn",
                                "adjacent faces with opposite winding", len(flipped),
                                [list(e) for e in flipped[:5]]))

    # Creases (> SHARP_DIHEDRAL_DEG) are intentional hard edges. Smooth edges
    # give a discrete curvature estimate: turning angle / centroid distance.
    sharp = 0
    max_curv = 0.0
    cos_sharp = math.cos(math.radians(SHARP_DIHEDRAL_DEG))
    for (eu, ev), fs in edge_faces.items():
        if len(fs) != 2:
            continue
        n1, n2 = normals[fs[0]], normals[fs[1]]
        d = max(-1.0, min(1.0, _dot(n1, n2)))
        if d < cos_sharp:
            sharp += 1
            continue
        c1 = [sum(V[k][i] for k in tris[fs[0]]) / 3 for i in range(3)]
        c2 = [sum(V[k][i] for k in tris[fs[1]]) / 3 for i in range(3)]
        # distance across the edge only: drop the component along it, which
        # would otherwise dominate for long, thin triangles
        delta = _sub(c1, c2)
        edge = _sub(V[ev], V[eu])
        el = _len(edge)
        if el == 0:
            continue
        along = _dot(delta, edge) / el
        dist = math.sqrt(max(_dot(delta, delta) - along * along, 0.0))
        if dist > 0:
            max_curv = max(max_curv, math.acos(d) / dist)
    stats["sharp_edges"] = sharp
    stats["max_curvature_per_m"] = max_curv
    if max_curv > 1.0 / limits.min_bend_radius_m:
        findings.append(Finding("high_curvature", "warn",
                                f"smallest bend radius ~{1000 / max_curv:.2g} mm "
                                f"(< {limits.min_bend_radius_m * 1000:g} mm): normal/LOD "
                                "artifacts, unstable collision hulls"))

    # duplicate (coincident) vertices at 1e-6 m resolution
    keys = Counter((round(x * 1e6), round(y * 1e6), round(z * 1e6)) for x, y, z in V)
    dupes = sum(c - 1 for c in keys.values() if c > 1)
    if dupes:
        findings.append(Finding("duplicate_vertices", "info",
                                "coincident vertices (unwelded seams)", dupes))

    # --- scale / bounding box ---------------------------------------------
    lo = [min(v[k] for v in V) for k in range(3)]
    hi = [max(v[k] for v in V) for k in range(3)]
    ext = [hi[k] - lo[k] for k in range(3)]
    stats["bbox_min"], stats["bbox_max"], stats["extent_m"] = lo, hi, ext
    largest = max(ext)
    smin, smax = limits.expected_size_m
    if largest > smax:
        guess = "cm authored as m (x100)" if 0.5 <= largest / 100 <= smax else "unknown unit"
        findings.append(Finding("scale_mismatch", "error",
                                f"largest extent {largest:.3g} m > {smax:g} m; likely {guess}"))
    elif largest < smin:
        findings.append(Finding("scale_mismatch", "error",
                                f"largest extent {largest:.3g} m < {smin:g} m; likely m authored as mm"))
    if largest > 0 and min(ext) / largest < THIN_RATIO:
        findings.append(Finding("thin_feature", "warn",
                                f"thinnest axis is {min(ext) / largest:.2%} of largest "
                                f"({min(ext) * 1000:.3g} mm): collision tunnelling / z-fighting risk"))
    if 0 < min_edge < math.inf and min_edge / max_edge < 1e-3:
        findings.append(Finding("edge_length_range", "warn",
                                f"edge lengths span {max_edge / min_edge:.0f}x; float precision risk"))

    # --- mass properties (only meaningful when watertight) -------------------
    watertight = not boundary and not nonmanifold
    stats["watertight"] = watertight
    if watertight and abs(vol6) > 1e-18:
        volume = vol6 / 6.0
        c = [com[k] / (4.0 * vol6) for k in range(3)]
        bc = [(lo[k] + hi[k]) / 2 for k in range(3)]
        offset = max(abs(c[k] - bc[k]) / ext[k] for k in range(3) if ext[k] > 0)
        stats["volume_m3"] = volume
        stats["center_of_mass"] = c
        stats["com_offset_ratio"] = offset
        if volume < 0:
            findings.append(Finding("inverted_normals", "warn",
                                    "negative signed volume: faces point inward"))
        if offset > limits.max_com_offset:
            findings.append(Finding("asymmetric_mass", "warn",
                                    f"center of mass is offset {offset:.0%} of the extent from "
                                    "bbox center: pivots/physics will tip"))

    # --- GPU memory footprint -------------------------------------------------
    index_bytes = 2 if len(V) <= 65535 else 4
    vram = len(V) * VERTEX_STRIDE + len(tris) * 3 * index_bytes
    stats["index_format"] = f"uint{index_bytes * 8}"
    stats["vram_bytes"] = vram
    if index_bytes == 4:
        findings.append(Finding("index_overflow_16bit", "warn",
                                f"{len(V)} vertices > 65535: needs 32-bit indices "
                                "(unsupported/slow on some mobile GPUs)"))
    if vram > limits.vram_budget_bytes:
        findings.append(Finding("vram_budget", "error",
                                f"{vram / 2**20:.2f} MiB > budget "
                                f"{limits.vram_budget_bytes / 2**20:.2f} MiB"))
    return _result(mesh, stats, findings)


def _result(mesh: Mesh, stats: dict, findings: list[Finding]) -> dict:
    worst = "pass"
    if any(f.severity == "error" for f in findings):
        worst = "fail"
    elif any(f.severity == "warn" for f in findings):
        worst = "warn"
    return {
        "asset": mesh.name,
        "status": worst,
        "stats": stats,
        "findings": [f.__dict__ for f in findings],
    }
