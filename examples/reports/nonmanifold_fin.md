# nonmanifold_fin: FAIL

| stat | value |
|---|---|
| vertices | 9 |
| faces | 7 |
| triangles | 13 |
| surface_area_m2 | 6.43 |
| min_edge_m | 0.8602 |
| max_edge_m | 1.414 |
| edges | 20 |
| sharp_edges | 11 |
| max_curvature_per_m | 0 |
| bbox_min | [-0.5, -0.5, -0.5] |
| bbox_max | [1, 0.5, 1.2] |
| extent_m | [1.5, 1, 1.7] |
| watertight | False |
| index_format | uint16 |
| vram_bytes | 366 |

| severity | check | count | detail |
|---|---|---:|---|
| error | non_manifold_edges | 1 | edges shared by more than two faces |
| warn | boundary_edges | 2 | open edges: mesh is not watertight |

Check time: 0.5 ms
