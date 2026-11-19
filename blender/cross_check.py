"""Cross-validate meshstress against Blender's own bmesh topology queries.

Run headless:
    blender -b --factory-startup -P blender/cross_check.py -- examples/objs/*.obj

Prints one JSON line per file with Blender's counts for non-manifold edges,
boundary edges and zero-area faces, so you can diff them against meshstress.
Uses only bpy/bmesh, which ship with Blender.
"""
import json
import sys

import bmesh  # type: ignore
import bpy  # type: ignore

AREA_EPS = 1e-12


def load_obj(path):
    """Minimal OBJ reader (v/f only) so results don't depend on importer
    options such as auto-merge, split-by-group or axis conversion."""
    verts, faces = [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            p = line.split()
            if not p:
                continue
            if p[0] == "v":
                verts.append(tuple(float(x) for x in p[1:4]))
            elif p[0] == "f":
                faces.append([int(t.split("/")[0]) - 1 for t in p[1:]])
    return verts, faces


def check(path):
    verts, faces = load_obj(path)
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    skipped = 0
    for f in faces:
        try:
            bm.faces.new([bv[i] for i in f])
        except ValueError:  # duplicate face or repeated vertex: bmesh refuses it
            skipped += 1
    bm.edges.ensure_lookup_table()
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    zero_area = sum(1 for f in bm.faces if f.calc_area() < AREA_EPS)
    result = {"file": path, "blender": bpy.app.version_string,
              "faces_rejected_by_bmesh": skipped, "non_manifold_edges": nonmanifold,
              "boundary_edges": boundary, "zero_area_faces": zero_area}
    bm.free()
    return result


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for p in args:
        print("MESHSTRESS_XCHECK " + json.dumps(check(p)))
