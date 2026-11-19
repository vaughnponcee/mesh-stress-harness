"""Minimal indexed triangle mesh with OBJ I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

Vec = tuple[float, float, float]


@dataclass
class Mesh:
    name: str
    verts: list[Vec] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)  # 0-based indices

    def add_vert(self, v: Vec) -> int:
        self.verts.append((float(v[0]), float(v[1]), float(v[2])))
        return len(self.verts) - 1

    def add_face(self, *idx: int) -> None:
        self.faces.append(tuple(idx))

    def triangles(self) -> list[tuple[int, int, int]]:
        """Fan-triangulate n-gons (fine for the convex quads generators emit)."""
        tris = []
        for f in self.faces:
            for i in range(1, len(f) - 1):
                tris.append((f[0], f[i], f[i + 1]))
        return tris

    def merge(self, other: "Mesh") -> "Mesh":
        off = len(self.verts)
        self.verts.extend(other.verts)
        self.faces.extend(tuple(i + off for i in f) for f in other.faces)
        return self

    def transformed(self, scale: Vec = (1, 1, 1), offset: Vec = (0, 0, 0)) -> "Mesh":
        m = Mesh(self.name)
        m.verts = [(x * scale[0] + offset[0], y * scale[1] + offset[1], z * scale[2] + offset[2])
                   for x, y, z in self.verts]
        m.faces = list(self.faces)
        return m


def write_obj(mesh: Mesh, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# meshstress: {mesh.name}", f"o {mesh.name}"]
    lines += [f"v {x:.9g} {y:.9g} {z:.9g}" for x, y, z in mesh.verts]
    lines += ["f " + " ".join(str(i + 1) for i in f) for f in mesh.faces]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def read_obj(path: str | Path) -> Mesh:
    """Reads v/f records (ignores uv/normal indices, groups, materials).
    Negative (relative) indices are supported."""
    path = Path(path)
    mesh = Mesh(path.stem)
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "o" and len(parts) > 1:
            mesh.name = parts[1]
        elif parts[0] == "v":
            mesh.add_vert(tuple(float(p) for p in parts[1:4]))
        elif parts[0] == "f":
            idx = []
            for tok in parts[1:]:
                i = int(tok.split("/")[0])
                idx.append(i - 1 if i > 0 else len(mesh.verts) + i)
            mesh.add_face(*idx)
    return mesh
