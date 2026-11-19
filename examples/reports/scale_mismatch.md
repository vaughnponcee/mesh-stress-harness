# scale_mismatch: FAIL

| stat | value |
|---|---|
| vertices | 48 |
| faces | 36 |
| triangles | 72 |
| surface_area_m2 | 1.273e+04 |
| min_edge_m | 4 |
| max_edge_m | 63.64 |
| edges | 108 |
| sharp_edges | 72 |
| max_curvature_per_m | 0 |
| bbox_min | [-22.5, -22.5, 0] |
| bbox_max | [22.5, 22.5, 92.5] |
| extent_m | [45, 45, 92.5] |
| watertight | True |
| volume_m3 | 2.11e+04 |
| center_of_mass | [0, 7.868, 51.52] |
| com_offset_ratio | 0.1748 |
| index_format | uint16 |
| vram_bytes | 1968 |

| severity | check | count | detail |
|---|---|---:|---|
| info | duplicate_vertices | 2 | coincident vertices (unwelded seams) |
| error | scale_mismatch |  | largest extent 92.5 m > 10 m; likely cm authored as m (x100) |

Check time: 1.3 ms
