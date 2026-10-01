import errno
import json
import unittest
from habitat_prototype.measurement import *


class MeasurementTests(unittest.TestCase):
    def test_zero_is_observed_and_absence_is_not_zero(self):
        self.assertEqual(Quantity(State.OBSERVED, Unit.COUNT, Scope.SYNTHETIC, 0).as_dict()["value"], 0)
        self.assertNotIn("value", Quantity(State.UNAVAILABLE, Unit.COUNT, Scope.SYNTHETIC).as_dict())

    def test_unlimited_is_distinct(self):
        self.assertEqual(parse_limit("max\n").state, State.UNLIMITED)
        self.assertEqual(parse_limit("0\n").value, 0)

    def test_values_are_finite_nonnegative_and_not_boolean(self):
        for value in (True, False, float("nan"), float("inf"), -1, "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Quantity(State.OBSERVED, Unit.COUNT, Scope.SYNTHETIC, value)

    def test_nonobserved_values_cannot_leak(self):
        for state in State:
            if state != State.OBSERVED:
                with self.assertRaises(ValueError):
                    Quantity(state, Unit.COUNT, Scope.SYNTHETIC, 0)

    def test_enum_types_required(self):
        with self.assertRaises(ValueError):
            Quantity("observed", Unit.COUNT, Scope.SYNTHETIC, 2)

    def test_malformed_numbers(self):
        for raw in ("", "NaN", "-2", "3.5", "+2", "∞", "1" * 129, "0x10", None):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_nonnegative_integer(raw)

    def test_typed_exception_states_no_path_messages(self):
        cases = [(PermissionError("/secret/path"), State.DENIED),
                 (FileNotFoundError("/private/name"), State.UNAVAILABLE),
                 (NotImplementedError("private"), State.UNSUPPORTED),
                 (OSError(errno.ENOSYS, "private"), State.UNSUPPORTED),
                 (OSError(errno.EIO, "private"), State.TRANSIENT),
                 (ValueError("secret"), State.MALFORMED)]
        for error, expected in cases:
            def reader(error=error):
                raise error
            q = capture(reader, unit=Unit.BYTES, scope=Scope.SYNTHETIC)
            self.assertEqual(q.state, expected)
            self.assertNotIn("private", json.dumps(q.as_dict()))
            self.assertNotIn("secret", json.dumps(q.as_dict()))

    def test_programming_errors_not_hidden(self):
        def reader():
            raise TypeError("programmer error")
        with self.assertRaises(TypeError):
            capture(reader, unit=Unit.BYTES, scope=Scope.SYNTHETIC)

    def test_capture_parser(self):
        self.assertEqual(capture(lambda: "42\n", unit=Unit.COUNT, scope=Scope.SYNTHETIC).value, 42)
        self.assertEqual(capture(lambda: "max", unit=Unit.BYTES, scope=Scope.CGROUP, limit=True).state, State.UNLIMITED)

    def test_injected_clock_read_order(self):
        calls, monos = [], iter([5, 9])
        def mono():
            calls.append("mono")
            return next(monos)
        def wall():
            calls.append("wall")
            return 100
        def cpu():
            calls.append("cpu")
            return 2
        value = stamp(mono, wall, cpu, epoch="fixture")
        self.assertEqual(calls, ["mono", "wall", "cpu", "mono"])
        self.assertEqual((value.monotonic_before_ns, value.monotonic_after_ns), (5, 9))

    def test_exact_interval_bounds(self):
        a, b = ClockStamp(0, 100, 0, 4, "x"), ClockStamp(100, 200, 25, 106, "x")
        result = paired_interval(a, b, jump_tolerance_ns=0)
        self.assertEqual(result["elapsed_ns"], {"lower": 96, "upper": 106, "midpoint_twice": 202})
        self.assertFalse(result["clock_discrepancy"])
        self.assertEqual(result["cpu_per_elapsed"]["upper"], 25 / 96)

    def test_backwards_wall_is_discrepancy_not_negative_elapsed(self):
        result = paired_interval(ClockStamp(0, 200, 0, 0, "x"), ClockStamp(100, 100, 5, 100, "x"), jump_tolerance_ns=0)
        self.assertTrue(result["clock_discrepancy"])
        self.assertEqual(result["elapsed_ns"]["lower"], 100)
        self.assertEqual(result["clock_residual_ns_twice"], -400)

    def test_bracket_uncertainty_prevents_overclaim(self):
        result = paired_interval(ClockStamp(0, 100, 0, 10, "x"), ClockStamp(20, 130, 1, 40, "x"), jump_tolerance_ns=0)
        self.assertFalse(result["clock_discrepancy"])

    def test_cpu_ratios_above_one_are_preserved(self):
        r = paired_interval(ClockStamp(0, 0, 0, 0, "x"), ClockStamp(10, 10, 40, 10, "x"))
        self.assertEqual(r["cpu_per_elapsed"]["upper"], 4)

    def test_cpu_reset_and_zero_elapsed(self):
        r = paired_interval(ClockStamp(0, 0, 5, 0, "x"), ClockStamp(0, 0, 3, 0, "x"))
        self.assertEqual(r["process_cpu"]["state"], "counter_reset")
        self.assertEqual(r["cpu_per_elapsed"]["state"], "not_identifiable")

    def test_incompatible_or_overlapping_clock_epochs(self):
        a = ClockStamp(0, 0, 0, 10, "x")
        for b in (ClockStamp(20, 20, 1, 20, "y"), ClockStamp(9, 9, 1, 11, "x")):
            with self.assertRaises(ValueError):
                paired_interval(a, b)

    def test_integer_precision_at_large_monotonic_origin(self):
        n = 10 ** 20
        r = paired_interval(ClockStamp(n, n, 0, n+1, "x"), ClockStamp(n+9, n+9, 1, n+10, "x"))
        self.assertEqual(r["elapsed_ns"]["midpoint_twice"], 18)

    def test_bracket_regression_rejected(self):
        with self.assertRaises(ValueError):
            ClockStamp(5, 0, 0, 4, "x")
