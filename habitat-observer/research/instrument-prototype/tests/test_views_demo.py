import ast
import json
from pathlib import Path
import unittest
import demo
from habitat_prototype.cadence import Claim, MissedSpan
from habitat_prototype.measurement import Quantity, State, Scope, Unit
from habitat_prototype.views import *


class ViewTests(unittest.TestCase):
    def q(self, n, scope=Scope.SYNTHETIC):
        return Quantity(State.OBSERVED, Unit.NANOSECONDS, scope, n)

    def test_cadence_slots_are_not_interpolated(self):
        p = cadence_projection(6, [Claim(0, 0, 0), Claim(2, 20, 21)],
                               [MissedSpan(3, 4, "observer_overrun")], elapsed_slots=5, width=6)
        self.assertEqual(p["glyphs"], "●?◔×?·")
        self.assertEqual(p["counts"]["unknown"], 2)

    def test_compressed_mixture_retains_exact_counts(self):
        p = cadence_projection(4, [Claim(0, 0, 0)], [MissedSpan(1, 4, "delayed_wake")], elapsed_slots=4, width=1)
        self.assertEqual(p["glyphs"], "◆")
        self.assertEqual(p["bins"][0]["counts"], {"on_time": 1, "missed": 3})

    def test_future_is_not_unknown(self):
        p = cadence_projection(10, [], [], elapsed_slots=3, width=2)
        self.assertEqual(p["counts"], {"unknown": 3, "future": 7})

    def test_evidence_overlap_and_future_rejected(self):
        for claims, spans in (([Claim(0, 0, 0), Claim(0, 0, 0)], []),
                               ([Claim(0, 0, 0)], [MissedSpan(0, 2, "delayed_wake")]),
                               ([Claim(4, 40, 40)], [])):
            with self.assertRaises(ValueError):
                cadence_projection(6, claims, spans, elapsed_slots=3)

    def test_ascii_output(self):
        p = cadence_projection(3, [Claim(0, 0, 0)], [], elapsed_slots=2, ascii_only=True)
        rendered = render_cadence(p, ascii_only=True)
        self.assertTrue(rendered.isascii())
        self.assertEqual(p["glyphs"], "o?.")

    def test_fixed_bins_boundary_and_observed_zero(self):
        d = cost_distribution([self.q(0), self.q(100), self.q(101)], edges_ns=(100,))
        self.assertEqual(d["bin_counts"], [1, 2])
        self.assertEqual(d["observed_count"], 3)

    def test_missingness_retained_outside_distribution(self):
        values = [self.q(0), Quantity(State.DENIED, Unit.NANOSECONDS, Scope.SYNTHETIC)]
        d = cost_distribution(values)
        self.assertEqual(d["observed_count"], 1)
        self.assertEqual(d["missing_by_state"], {"permission_denied": 1})

    def test_sparse_tail_gates(self):
        d = cost_distribution([self.q(i) for i in range(19)])
        self.assertIsNone(d["p95_ns"])
        self.assertIsNone(d["p99_ns"])
        self.assertEqual(cost_distribution([self.q(i) for i in range(20)])["p95_ns"], 18)
        self.assertEqual(cost_distribution([self.q(i) for i in range(100)])["p99_ns"], 98)

    def test_empty_histogram_no_fabricated_statistics(self):
        d = cost_distribution([])
        self.assertIsNone(d["minimum_ns"])
        self.assertIsNone(d["p50_ns"])
        self.assertEqual(sum(d["bin_counts"]), 0)

    def test_no_cross_scope_pooling(self):
        with self.assertRaises(ValueError):
            cost_distribution([self.q(1), self.q(2, Scope.PROCESS)])

    def test_cost_matrix_empty_values_and_ascii(self):
        self.assertTrue(render_cost_matrix({"empty": []}, ascii_only=True).isascii())
        with self.assertRaises(ValueError):
            render_cost_matrix({"bad\nlabel": []})

    def test_projection_resource_limits(self):
        with self.assertRaises(ValueError):
            cadence_projection(100001, [], [], elapsed_slots=0)
        with self.assertRaises(ValueError):
            cadence_projection(10, [], [], elapsed_slots=0, width=97)


class SyntheticDemoTests(unittest.TestCase):
    def test_demo_reproducible_and_json_finite(self):
        a, text_a = demo.fixture()
        b, text_b = demo.fixture()
        self.assertEqual(a, b)
        self.assertEqual(text_a, text_b)
        json.dumps(a, allow_nan=False)
        self.assertTrue(a["synthetic"])
        self.assertIn("SYNTHETIC FIXTURES ONLY", text_a)
        self.assertEqual(a["cadence"]["claimed_slots"] + a["cadence"]["missed_slots"], 12)

    def test_instrument_modules_have_no_execution_primitives(self):
        # Regression tripwire, not a general security proof. All I/O belongs to
        # a future reviewed adapter. The demo only prints synthetic results.
        root = Path(__file__).resolve().parents[1] / "habitat_prototype"
        prohibited_imports = {"os", "time", "socket", "subprocess", "requests", "urllib", "pathlib", "resource", "threading", "multiprocessing"}
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({n.name.split(".")[0] for n in node.names} & prohibited_imports, path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], prohibited_imports, path.name)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"open", "exec", "eval", "__import__"}, path.name)
