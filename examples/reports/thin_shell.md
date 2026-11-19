# thin_shell: WARN

| stat | value |
|---|---|
| vertices | 8 |
| faces | 6 |
| triangles | 12 |
| surface_area_m2 | 2.002 |
| min_edge_m | 0.0005 |
| max_edge_m | 1.414 |
| edges | 18 |
| sharp_edges | 12 |
| max_curvature_per_m | 0 |
| bbox_min | [-0.5, -0.5, -0.00025] |
| bbox_max | [0.5, 0.5, 0.00025] |
| extent_m | [1, 1, 0.0005] |
| watertight | True |
| volume_m3 | 0.0005 |
| center_of_mass | [0, 0, 0] |
| com_offset_ratio | 0 |
| index_format | uint16 |
| vram_bytes | 328 |

| severity | check | count | detail |
|---|---|---:|---|
| warn | sliver_triangles | 8 | needle/sliver triangles (aspect > 50) |
| warn | thin_feature |  | thinnest axis is 0.05% of largest (0.5 mm): collision tunnelling / z-fighting risk |
| warn | edge_length_range |  | edge lengths span 2828x; float precision risk |

Check time: 0.6 ms
