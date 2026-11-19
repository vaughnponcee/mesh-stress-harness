"""Procedural stress-test geometry.

Every generator is deterministic for a given seed and returns a Mesh in
metres. "Clean" generators should pass all checks; "broken" ones each
plant a specific, known defect so the checks themselves can be verified.
"""
from __future__ import annotations

import math
import random

from .mesh import Mesh


# ---------------------------------------------------------------- primitives
def box(name: str, sx: float, sy: float, sz: float, center=(0.0, 0.0, 0.0)) -> Mesh:
    m = Mesh(name)
    cx, cy, cz = center
    for dx in (-1, 1):
        for dy in (-1, 1):
            for dz in (-1, 1):
                m.add_vert((cx + dx * sx / 2, cy + dy * sy / 2, cz + dz * sz / 2))
    # vertex index = (dx>0)*4 + (dy>0)*2 + (dz>0); outward-facing quads
    for q in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
        m.add_face(*q)
    return m


def uv_sphere(name: str, radius: float, rings: int = 16, segments: int = 32,
              center=(0.0, 0.0, 0.0), squash=(1.0, 1.0, 1.0)) -> Mesh:
    m = Mesh(name)
    cx, cy, cz = center
    top = m.add_vert((cx, cy, cz + radius * squash[2]))
    for r in range(1, rings):
        phi = math.pi * r / rings
        for s in range(segments):
            th = 2 * math.pi * s / segments
            m.add_vert((cx + radius * squash[0] * math.sin(phi) * math.cos(th),
                        cy + radius * squash[1] * math.sin(phi) * math.sin(th),
                        cz + radius * squash[2] * math.cos(phi)))
    bot = m.add_vert((cx, cy, cz - radius * squash[2]))

    def ring(r, s):
        return 1 + (r - 1) * segments + (s % segments)

    for s in range(segments):
        m.add_face(top, ring(1, s), ring(1, s + 1))
        m.add_face(bot, ring(rings - 1, s + 1), ring(rings - 1, s))
    for r in range(1, rings - 1):
        for s in range(segments):
            m.add_face(ring(r, s), ring(r + 1, s), ring(r + 1, s + 1), ring(r, s + 1))
    return m


def torus(name: str, major: float, minor: float, seg_u: int = 48, seg_v: int = 24) -> Mesh:
    m = Mesh(name)
    for i in range(seg_u):
        u = 2 * math.pi * i / seg_u
        for j in range(seg_v):
            v = 2 * math.pi * j / seg_v
            m.add_vert(((major + minor * math.cos(v)) * math.cos(u),
                        (major + minor * math.cos(v)) * math.sin(u),
                        minor * math.sin(v)))
    for i in range(seg_u):
        for j in range(seg_v):
            a = i * seg_v + j
            b = ((i + 1) % seg_u) * seg_v + j
            c = ((i + 1) % seg_u) * seg_v + (j + 1) % seg_v
            d = i * seg_v + (j + 1) % seg_v
            m.add_face(a, b, c, d)
    return m


# ------------------------------------------------------------ clean stressors
def thin_shell(thickness: float = 0.0005, size: float = 1.0) -> Mesh:
    """A 1 m panel only 0.5 mm thick: a closed solid, but a nightmare for
    collision, shadow bias and float precision."""
    return box("thin_shell", size, size, thickness)


def high_curvature_joint(seed: int = 0, minor: float = 0.003) -> Mesh:
    """A torus whose tube radius is tiny relative to the ring: extreme
    curvature, slivers along the inner seam, very short edges."""
    return torus("high_curvature_joint", major=0.5, minor=minor, seg_u=96, seg_v=24)


def asymmetric_mass(seed: int = 0) -> Mesh:
    """A hammer: thin 1 m handle, heavy offset head. Two closed shells; the
    center of mass sits far from the bounding-box center (and the pivot)."""
    rng = random.Random(seed)
    handle = box("asymmetric_mass", 0.03, 0.03, 1.0, center=(0, 0, 0.5))
    head_len = 0.30 + rng.uniform(0, 0.05)
    head = box("head", head_len, 0.08, 0.10, center=(head_len / 2 - 0.04, 0, 1.05))
    return handle.merge(head)


def dense_scan(seed: int = 0, rings: int = 256, segments: int = 512) -> Mesh:
    """A photogrammetry-like dense sphere with noisy radius: tests VRAM
    budgets and index-width (16 vs 32 bit) overflow."""
    rng = random.Random(seed)
    m = uv_sphere("dense_scan", 0.3, rings=rings, segments=segments)
    m.verts = [(x * k, y * k, z * k) for (x, y, z) in m.verts
               for k in [1 + rng.uniform(-0.01, 0.01)]]
    return m


# ------------------------------------------------- deliberately broken assets
def nonmanifold_fin() -> Mesh:
    """A cube with an extra fin sharing one cube edge -> edge used by 3 faces."""
    m = box("nonmanifold_fin", 1, 1, 1)
    a, b = 4 + 2 + 1, 4 + 1  # edge (+x,+y,+z)-(+x,-y,+z)
    c = m.add_vert((1.0, 0.5, 1.2))
    m.add_face(a, b, c)
    return m


def degenerate_tris() -> Mesh:
    """A clean box plus a zero-area triangle (collinear) and a collapsed one
    (repeated index): classic exporter garbage."""
    m = box("degenerate_tris", 1, 1, 1)
    p = m.add_vert((0.0, 0.0, 0.5))
    q = m.add_vert((0.25, 0.0, 0.5))
    r = m.add_vert((0.5, 0.0, 0.5))
    m.add_face(p, q, r)
    m.add_face(p, p, q)
    return m


def scale_mismatch() -> Mesh:
    """A 'chair' authored in centimetres but tagged as metres: 90 m tall."""
    seat = box("scale_mismatch", 45, 45, 5, center=(0, 0, 45))
    for x in (-20, 20):
        for y in (-20, 20):
            seat.merge(box("leg", 4, 4, 45, center=(x, y, 22.5)))
    back = box("back", 45, 4, 45, center=(0, 20.5, 70))
    return seat.merge(back)


def open_shell() -> Mesh:
    """A box missing its top face: boundary edges, undefined volume."""
    m = box("open_shell", 1, 1, 1)
    m.faces = [f for f in m.faces if f != (1, 5, 7, 3)]
    return m


CLEAN = {
    "thin_shell": thin_shell,
    "high_curvature_joint": high_curvature_joint,
    "asymmetric_mass": asymmetric_mass,
    "dense_scan": dense_scan,
}
BROKEN = {
    "nonmanifold_fin": nonmanifold_fin,
    "degenerate_tris": degenerate_tris,
    "scale_mismatch": scale_mismatch,
    "open_shell": open_shell,
}
ALL = {**CLEAN, **BROKEN}
