# Mesh stress-test summary

| asset | status | tris | VRAM KiB | errors | warnings | ms |
|---|---|---:|---:|---:|---:|---:|
| thin_shell | warn | 12 | 0.3 | 0 | 3 | 0.6 |
| high_curvature_joint | warn | 4608 | 99.0 | 0 | 1 | 93.5 |
| asymmetric_mass | warn | 24 | 0.6 | 0 | 1 | 0.4 |
| nonmanifold_fin | fail | 13 | 0.4 | 1 | 1 | 0.5 |
| degenerate_tris | fail | 14 | 0.4 | 1 | 0 | 0.3 |
| scale_mismatch | fail | 72 | 1.9 | 1 | 0 | 1.3 |
| open_shell | warn | 10 | 0.3 | 0 | 1 | 0.2 |
