# meshstress

Procedural stress-test geometry plus automated mesh diagnostics. It is pure Python (3.10+, standard library only), with an optional Blender script that cross-checks the topology results.

The harness generates assets that break real pipelines: 0.5 mm shells, 3 mm bend radii, top-heavy props, 130k-vertex scans, and deliberately corrupted exports. It then runs every check against them and writes one JSON report and one Markdown report per asset.

```bash
python -m meshstress list                         # what the generators make
python -m meshstress suite -o reports/ --obj-dir out/
python -m meshstress check model.obj other.obj -o reports/ --vram-mib 4
```

`check` exits with status 1 if any asset has an `error`, so it can gate CI.

## Generated assets

| asset | kind | what it stresses |
|---|---|---|
| `thin_shell` | clean | 1 m × 1 m × 0.5 mm closed panel: tunnelling, shadow bias, sliver faces |
| `high_curvature_joint` | clean | torus with a 3 mm tube on a 0.5 m ring: tiny bend radius, 40:1 edge ratio |
| `asymmetric_mass` | clean | hammer: 1 m handle, heavy offset head; center of mass far from the pivot |
| `dense_scan` | clean | noisy 261k-triangle sphere: VRAM budget and 16-bit index overflow |
| `nonmanifold_fin` | broken | cube with a fin sharing one edge (3 faces on an edge) |
| `degenerate_tris` | broken | a collinear triangle plus a collapsed `(p, p, q)` triangle |
| `scale_mismatch` | broken | chair authored in cm but read as m (92.5 m tall) |
| `open_shell` | broken | cube missing a face |

"Clean" means topologically valid. They are supposed to produce warnings. The sample OBJ files and their reports are committed in [`examples/`](examples/).

## Checks

| check | severity | method |
|---|---|---|
| `non_manifold_edges` | error | undirected edge → face count > 2 |
| `boundary_edges` | warn | edge → face count == 1 |
| `inconsistent_winding` | warn | the same directed edge appears twice |
| `degenerate_triangles` | error | repeated index, or area < 1e-12 m² |
| `sliver_triangles` | warn/info | longest edge² / (2·area) > 50 |
| `duplicate_vertices` | info | vertices hashed on a 1 µm grid |
| `scale_mismatch` | error | largest extent outside 1 cm to 10 m; guesses ×100 or ×0.001 |
| `thin_feature` | warn | thinnest extent / largest extent < 0.5% |
| `edge_length_range` | warn | max/min edge length > 1000 |
| `high_curvature` | warn | smallest bend radius < 5 mm (see below) |
| `inverted_normals` | warn | signed volume < 0 |
| `asymmetric_mass` | warn | center of mass offset > 20% of the extent on any axis |
| `index_overflow_16bit` | warn | more than 65,535 vertices |
| `vram_budget` | error | estimated GPU bytes > budget (default 8 MiB) |

### The maths, briefly

- **Volume and center of mass** use the divergence theorem. Each triangle forms a signed tetrahedron with the origin: `V = Σ a·(b×c) / 6` and `C = Σ (a·(b×c))(a+b+c) / (4 Σ a·(b×c))`. They are only reported when the mesh is watertight.
- **Curvature** is estimated per smooth edge as the dihedral angle divided by the distance between the two face centroids, measured perpendicular to the shared edge. Without that projection, long thin triangles underestimate curvature by about 20×; the first version had exactly that bug. Edges sharper than 60° are treated as intentional creases and skipped, so a cube reports zero curvature. On the 3 mm torus the estimate is 2.0 mm.
- **VRAM** = `vertices × 32 B` (float3 position, float3 normal, float2 uv) + `triangles × 3 × (2 or 4) B`. This is a lower bound: it ignores tangents, skinning weights, extra UV sets, padding and the driver's alignment.

## Benchmarks

`analyze()` on `dense_scan` at increasing resolution. Measured on Windows 11, Python 3.14, one core. Peak memory comes from a separate `tracemalloc` pass.

| triangles | vertices | check time (s) | peak Python heap (MiB) | est. VRAM (MiB) | index |
|---:|---:|---:|---:|---:|---|
| 3,968 | 1,986 | 0.08 | 4 | 0.08 | uint16 |
| 16,128 | 8,066 | 0.31 | 16 | 0.34 | uint16 |
| 65,024 | 32,514 | 1.25 | 64 | 1.36 | uint16 |
| 261,120 | 130,562 | 5.08 | 256 | 6.97 | uint32 |

Both time and memory grow linearly at about 20 µs and 1 KiB per triangle. The whole 8-asset suite runs in about 6 s, and almost all of that is `dense_scan`. Run with `--profile-mem` to add peak memory to the reports. It is off by default because `tracemalloc` makes the checks about 5× slower.

### Blender cross-check

```bash
blender -b --factory-startup -P blender/cross_check.py -- examples/objs/*.obj
```

On Blender 5.1.2, Blender's `bmesh` agrees with meshstress on the non-manifold and boundary edge counts for every sample. The one expected difference is `degenerate_tris`. `bmesh` refuses to create the collapsed `(p, p, q)` face and counts the collinear triangle's edges as boundary. meshstress reports both triangles as degenerate and excludes them from the topology checks.

## Limitations

- **Single-threaded pure Python.** About 260k triangles in 5 s. For multi-million-triangle scans, port `analyze()` to NumPy; the per-triangle loop vectorizes directly.
- **No self-intersection test.** Overlapping shells, such as the hammer's head and handle if they overlapped, would inflate the volume. A proper test needs a BVH and triangle–triangle intersection.
- **The thin-feature check uses the bounding box.** It catches a thin panel, but not a thin wall inside a thick object. That needs ray casting along the normals.
- **OBJ only**, positions and faces only. UVs, normals and materials are ignored. N-gons are fan-triangulated, which is only correct for convex faces.
- **Thresholds are opinions** (5 mm bend radius, 8 MiB, 1 cm to 10 m). Change them through `Limits` or the CLI flags.

## Layout

```
meshstress/   mesh.py (OBJ I/O) · generators.py · checks.py · report.py · cli.py
blender/      cross_check.py (optional, runs inside Blender)
examples/     objs/ (sample inputs) · reports/ (generated output)
tests/        21 unittest cases
```

```bash
python -m unittest discover -s tests -t .
```

## License

MIT
