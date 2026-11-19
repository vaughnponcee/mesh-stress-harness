import json
import tempfile
import unittest
from pathlib import Path

from meshstress import generators as g
from meshstress.checks import Limits, analyze
from meshstress.cli import main
from meshstress.mesh import Mesh, read_obj, write_obj

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "objs"


def checks(result, severity=None):
    return {f["check"] for f in result["findings"]
            if severity is None or f["severity"] == severity}


class PrimitiveTests(unittest.TestCase):
    def test_unit_box_is_clean_and_outward(self):
        r = analyze(g.box("cube", 1, 1, 1))
        self.assertEqual(r["status"], "pass", r["findings"])
        self.assertAlmostEqual(r["stats"]["volume_m3"], 1.0, places=9)
        self.assertAlmostEqual(r["stats"]["surface_area_m2"], 6.0, places=9)
        self.assertTrue(r["stats"]["watertight"])

    def test_sphere_volume_converges(self):
        r = analyze(g.uv_sphere("s", 1.0, rings=64, segments=128))
        self.assertAlmostEqual(r["stats"]["volume_m3"], 4 / 3 * 3.14159265, delta=0.01)
        self.assertNotIn("boundary_edges", checks(r))

    def test_torus_watertight(self):
        r = analyze(g.torus("t", 0.5, 0.1))
        self.assertTrue(r["stats"]["watertight"])
        self.assertEqual(r["stats"]["edges"], r["stats"]["triangles"] * 3 // 2)

    def test_inverted_box_detected(self):
        m = g.box("inv", 1, 1, 1)
        m.faces = [tuple(reversed(f)) for f in m.faces]
        r = analyze(m)
        self.assertIn("inverted_normals", checks(r))
        self.assertAlmostEqual(r["stats"]["volume_m3"], -1.0, places=9)

    def test_inconsistent_winding(self):
        m = g.box("flip1", 1, 1, 1)
        m.faces[0] = tuple(reversed(m.faces[0]))
        self.assertIn("inconsistent_winding", checks(analyze(m)))

    def test_empty_and_bad_index(self):
        self.assertIn("empty", checks(analyze(Mesh("e"))))
        m = Mesh("bad", [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 7)])
        self.assertEqual(analyze(m)["status"], "fail")


class StressorTests(unittest.TestCase):
    def test_thin_shell(self):
        r = analyze(g.thin_shell())
        self.assertIn("thin_feature", checks(r, "warn"))
        self.assertTrue(r["stats"]["watertight"])

    def test_high_curvature(self):
        r = analyze(g.high_curvature_joint())
        self.assertIn("high_curvature", checks(r, "warn"))
        # true bend radius is 3 mm; the discrete estimate must be within 2x
        radius = 1 / r["stats"]["max_curvature_per_m"]
        self.assertTrue(0.0015 < radius < 0.006, radius)
        # a fat torus must NOT trigger it
        self.assertNotIn("high_curvature", checks(analyze(g.torus("fat", 0.5, 0.2))))

    def test_crease_is_not_curvature(self):
        self.assertEqual(analyze(g.box("c", 1, 1, 1))["stats"]["max_curvature_per_m"], 0)

    def test_asymmetric_mass(self):
        r = analyze(g.asymmetric_mass())
        self.assertIn("asymmetric_mass", checks(r, "warn"))
        self.assertGreater(r["stats"]["center_of_mass"][2], 0.7)
        self.assertNotIn("asymmetric_mass", checks(analyze(g.box("sym", 1, 2, 3))))

    def test_dense_scan_memory(self):
        m = g.dense_scan(rings=200, segments=400)  # 79,602 verts
        r = analyze(m)
        self.assertEqual(r["stats"]["index_format"], "uint32")
        self.assertIn("index_overflow_16bit", checks(r, "warn"))
        expected = len(m.verts) * 32 + r["stats"]["triangles"] * 3 * 4
        self.assertEqual(r["stats"]["vram_bytes"], expected)
        tight = analyze(m, Limits(vram_budget_bytes=1 * 2**20))
        self.assertIn("vram_budget", checks(tight, "error"))

    def test_small_mesh_uses_16bit(self):
        self.assertEqual(analyze(g.thin_shell())["stats"]["index_format"], "uint16")

    def test_determinism(self):
        a, b = g.dense_scan(seed=3, rings=16, segments=32), g.dense_scan(seed=3, rings=16, segments=32)
        self.assertEqual(a.verts, b.verts)


class BrokenAssetTests(unittest.TestCase):
    def test_each_planted_defect_is_caught(self):
        expected = {
            "nonmanifold_fin": "non_manifold_edges",
            "degenerate_tris": "degenerate_triangles",
            "scale_mismatch": "scale_mismatch",
            "open_shell": "boundary_edges",
        }
        for name, check in expected.items():
            self.assertIn(check, checks(analyze(g.BROKEN[name]())), name)

    def test_counts_match_blender_crosscheck(self):
        # numbers recorded from blender/cross_check.py on Blender 5.1.2
        self.assertEqual(self._count("nonmanifold_fin", "non_manifold_edges"), 1)
        self.assertEqual(self._count("nonmanifold_fin", "boundary_edges"), 2)
        self.assertEqual(self._count("open_shell", "boundary_edges"), 4)

    def _count(self, asset, check):
        r = analyze(g.BROKEN[asset]())
        return next(f["count"] for f in r["findings"] if f["check"] == check)

    def test_scale_guess(self):
        r = analyze(g.scale_mismatch())
        msg = next(f["message"] for f in r["findings"] if f["check"] == "scale_mismatch")
        self.assertIn("cm authored as m", msg)
        tiny = g.box("mm", 1, 1, 1).transformed(scale=(0.001, 0.001, 0.001))
        self.assertIn("scale_mismatch", checks(analyze(tiny), "error"))

    def test_clean_generators_have_no_errors(self):
        for name, fn in g.CLEAN.items():
            mesh = fn(rings=32, segments=64) if name == "dense_scan" else fn()
            self.assertNotEqual(analyze(mesh)["status"], "fail", name)


class IoTests(unittest.TestCase):
    def test_obj_roundtrip(self):
        m = g.asymmetric_mass()
        with tempfile.TemporaryDirectory() as d:
            m2 = read_obj(write_obj(m, Path(d) / "a.obj"))
        self.assertEqual(len(m2.verts), len(m.verts))
        self.assertEqual(m2.faces, m.faces)

    def test_obj_slash_and_negative_indices(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.obj"
            p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nf 1/1/1 2/1/1 -1/1/1\n")
            self.assertEqual(read_obj(p).faces, [(0, 1, 2)])

    def test_sample_objs_and_cli_reports(self):
        files = sorted(str(p) for p in EXAMPLES.glob("*.obj"))
        self.assertGreaterEqual(len(files), 7)
        with tempfile.TemporaryDirectory() as d:
            code = main(["check", *files, "-o", d])
            self.assertEqual(code, 1)  # broken samples must fail the run
            data = json.loads((Path(d) / "nonmanifold_fin.json").read_text())
            self.assertEqual(data["status"], "fail")
            self.assertIn("| asset | status |", (Path(d) / "SUMMARY.md").read_text())
            self.assertIn("non_manifold_edges", (Path(d) / "nonmanifold_fin.md").read_text())

    def test_clean_check_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(["check", str(EXAMPLES / "thin_shell.obj"), "-o", d]), 0)


if __name__ == "__main__":
    unittest.main()
