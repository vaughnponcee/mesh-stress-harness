# high_curvature_joint: WARN

| stat | value |
|---|---|
| vertices | 2304 |
| faces | 2304 |
| triangles | 4608 |
| surface_area_m2 | 0.05902 |
| min_edge_m | 0.0007832 |
| max_edge_m | 0.03292 |
| edges | 6912 |
| sharp_edges | 0 |
| max_curvature_per_m | 506.3 |
| bbox_min | [-0.503, -0.503, -0.003] |
| bbox_max | [0.503, 0.503, 0.003] |
| extent_m | [1.006, 1.006, 0.006] |
| watertight | True |
| volume_m3 | 8.775e-05 |
| center_of_mass | [1.207e-16, 2.893e-16, -8.41e-18] |
| com_offset_ratio | 1.402e-15 |
| index_format | uint16 |
| vram_bytes | 101376 |

| severity | check | count | detail |
|---|---|---:|---|
| warn | high_curvature |  | smallest bend radius ~2 mm (< 5 mm): normal/LOD artifacts, unstable collision hulls |

Check time: 93.5 ms
