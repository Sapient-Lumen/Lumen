import random
import unittest
from habitat_prototype.cadence import *


class CadenceTests(unittest.TestCase):
    def test_on_time_complete_keeps_grid(self):
        d = DeadlineLedger(100, 10, 30)
        c = d.claim(100)
        self.assertEqual(c.slot, 0)
        self.assertIsNone(d.complete(102))
        self.assertEqual(d.next_wake_ns, 110)

    def test_overrun_records_all_missed_slots(self):
        d = DeadlineLedger(0, 10, 100)
        d.claim(0)
        span = d.complete(31)
        self.assertEqual((span.first, span.stop, span.count), (1, 4, 3))
        self.assertEqual(d.next_wake_ns, 40)
        self.assertEqual(span.reason, "observer_overrun")

    def test_completion_exactly_on_deadline_does_not_skip(self):
        d = DeadlineLedger(0, 10, 100)
        d.claim(0)
        self.assertIsNone(d.complete(10))
        self.assertEqual(d.claim(10).slot, 1)

    def test_delayed_wake_claims_only_newest_due_slot(self):
        d = DeadlineLedger(0, 10, 100)
        c = d.claim(35)
        self.assertEqual((c.slot, c.lateness_ns), (3, 5))
        self.assertEqual((c.missed_before.first, c.missed_before.stop), (0, 3))
        self.assertEqual(c.missed_before.reason, "delayed_wake")

    def test_duration_is_exclusive(self):
        d = DeadlineLedger(0, 10, 30)
        self.assertIsNone(d.claim(30))
        self.assertEqual(d.close(30).count, 3)
        self.assertEqual(d.summary()["planned_slots"], 3)

    def test_nonmultiple_duration_keeps_last_partial_window(self):
        d = DeadlineLedger(0, 10, 25)
        self.assertEqual(d.total_slots, 3)
        self.assertEqual(d.claim(24).slot, 2)
        self.assertIsNone(d.complete(25))
        self.assertIsNone(d.close(25))

    def test_early_wake_no_claim(self):
        d = DeadlineLedger(0, 10, 30)
        d.claim(0)
        d.complete(1)
        self.assertIsNone(d.claim(5))
        self.assertEqual(d.next_slot, 1)

    def test_pending_cannot_double_claim_or_close(self):
        d = DeadlineLedger(0, 10, 30)
        d.claim(0)
        for operation in (lambda: d.claim(1), lambda: d.close(1)):
            with self.assertRaises(ValueError):
                operation()
        d.complete(1)
        with self.assertRaises(ValueError):
            d.complete(2)

    def test_closed_is_final(self):
        d = DeadlineLedger(0, 10, 30)
        d.close(1)
        with self.assertRaises(ValueError):
            d.claim(2)
        self.assertIsNone(d.next_wake_ns)

    def test_interruption_leaves_future_unclassified_as_missed(self):
        d = DeadlineLedger(0, 10, 100)
        d.close(25)
        s = d.summary()
        self.assertEqual((s["missed_slots"], s["remaining_slots"]), (3, 7))

    def test_monotonic_regression_rejected(self):
        d = DeadlineLedger(0, 10, 100)
        d.claim(10)
        with self.assertRaises(ValueError):
            d.complete(9)

    def test_bounds_and_invalid_spans(self):
        for args in ((0, 0, 10), (0, 1, 100001), (True, 1, 10), (0, 1.5, 10)):
            with self.assertRaises(ValueError):
                DeadlineLedger(*args)
        with self.assertRaises(ValueError):
            MissedSpan(2, 2, "delayed_wake")
        with self.assertRaises(ValueError):
            Claim(True, 0, 0)

    def test_randomized_exact_slot_conservation(self):
        # Deterministic synthetic time. No live clocks, sampling, or sleeping.
        rng = random.Random(20261001)
        for _ in range(250):
            period, duration = rng.randint(1, 10), rng.randint(10, 300)
            d = DeadlineLedger(0, period, duration)
            claimed, missed = set(), set()
            now = 0
            def add_span(span):
                if span:
                    slots = set(range(span.first, span.stop))
                    self.assertFalse(slots & missed)
                    self.assertFalse(slots & claimed)
                    missed.update(slots)
            while now < duration:
                now = max(now, d.next_wake_ns) + rng.randint(0, 20)
                if now >= duration:
                    break
                c = d.claim(now)
                if c is not None:
                    add_span(c.missed_before)
                    self.assertNotIn(c.slot, claimed | missed)
                    claimed.add(c.slot)
                    now += rng.randint(0, 20)
                    add_span(d.complete(now))
                self.assertTrue(d.summary()["conservation_holds"])
            add_span(d.close(max(now, duration)))
            self.assertEqual(claimed | missed, set(range(d.total_slots)))
            self.assertEqual(d.claimed, len(claimed))
            self.assertEqual(d.missed, len(missed))
