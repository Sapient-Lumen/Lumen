import dataclasses
import json
import unittest
from habitat_prototype.provenance import *
from habitat_prototype.probe_design import *


class ProvenanceTests(unittest.TestCase):
    def contract(self):
        return RunContract("fixture", "a"*64, "epoch", 0, 1_000_000_000, 60_000_000_000)

    def test_manifest_deterministic_hash_and_public_safe(self):
        c = self.contract()
        self.assertEqual(c.sha256, self.contract().sha256)
        self.assertEqual(len(c.sha256), 64)
        self.assertFalse(c.as_dict()["active_filesystem_probe_enabled"])
        self.assertNotIn("hostname", c.as_dict())

    def test_manifest_rejects_unsafe_and_invalid_inputs(self):
        c = self.contract()
        for kw in ({"run_id": "../path"}, {"code_sha256": "bad"}, {"duration_ns": 90_000_000_000_000},
                   {"period_ns": True}, {"period_ns": 1}, {"log_budget_bytes": 10},
                   {"terminal_reserve_bytes": 40000}, {"mode": "active"}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                dataclasses.replace(c, **kw)

    def test_terminal_reservation(self):
        b = ByteLedger(100, 10, 90)
        self.assertTrue(b.admit(90))
        self.assertFalse(b.admit(1))
        self.assertTrue(b.admit(10, terminal=True))
        self.assertEqual(b.used, 100)

    def test_terminal_is_once_and_last(self):
        b = ByteLedger(100, 10, 90)
        self.assertTrue(b.admit(1, terminal=True))
        self.assertFalse(b.admit(1))
        self.assertFalse(b.admit(1, terminal=True))

    def test_failed_admission_has_no_charge(self):
        b = ByteLedger(100, 10, 90)
        self.assertFalse(b.admit(91))
        self.assertFalse(b.admit(11, terminal=True))
        self.assertEqual(b.used, 0)

    def test_budget_uses_exact_encoded_utf8_bytes(self):
        data = canonical_bytes({"glyph": "●"})
        b = ByteLedger(100, 10, 90)
        self.assertTrue(b.admit(len(data)))
        self.assertEqual(b.used, len(data))

    def test_prefix_is_retained_without_assumed_censoring(self):
        e = lifetime_evidence(start_ns=10, last_validated_ns=30, clock_epoch_matches=True)
        self.assertEqual(e["recording_endpoint"], "nonterminal_retained_prefix")
        self.assertEqual(e["recorded_extent_ns"], 20)
        self.assertFalse(e["environment_death_observed"])

    def test_no_endpoint_automatically_assigns_statistical_censoring(self):
        for terminal_kind, terminal_reason in ((None, None), ("stop", "duration_complete"), ("stop", "write_error")):
            e = lifetime_evidence(start_ns=0, last_validated_ns=10, clock_epoch_matches=True,
                                  terminal_kind=terminal_kind, terminal_reason=terminal_reason)
            self.assertEqual(e["statistical_censoring_classification"], "not_established")

    def test_planned_stop_is_administrative_not_death(self):
        e = lifetime_evidence(start_ns=0, last_validated_ns=10, clock_epoch_matches=True,
                              terminal_kind="stop", terminal_reason="duration_complete")
        self.assertEqual(e["recording_endpoint"], "administrative_end_recorded")
        self.assertFalse(e["stop_record_proves_process_exit"])

    def test_other_stop_is_reported_not_death(self):
        e = lifetime_evidence(start_ns=0, last_validated_ns=10, clock_epoch_matches=True,
                              terminal_kind="stop", terminal_reason="write_error")
        self.assertEqual(e["recording_endpoint"], "reported_stop_recorded")
        self.assertFalse(e["continuous_availability_proven"])

    def test_epoch_mismatch_withholds_extent(self):
        e = lifetime_evidence(start_ns=0, last_validated_ns=10, clock_epoch_matches=False)
        self.assertIsNone(e["recorded_extent_ns"])

    def test_lifetime_invalid_terminal_evidence_rejected(self):
        for kw in ({"terminal_reason": "duration_complete"}, {"terminal_kind": "death"},
                   {"terminal_kind": "stop", "terminal_reason": "/secret/path"}):
            with self.assertRaises(ValueError):
                lifetime_evidence(start_ns=0, last_validated_ns=10, clock_epoch_matches=True, **kw)


class ProbeDesignTests(unittest.TestCase):
    def stages(self):
        return [StageResult(name, i*10, i*10+5) for i, name in enumerate(STAGES)]

    def plan(self, spec=None, **kw):
        args = dict(trial_index=0, now_ns=0, deadline_slack_ns=1_000_000_000)
        args.update(kw)
        return plan_trial(spec or ProbeSpec(), **args)

    def test_disabled_default_has_no_operations(self):
        self.assertEqual(self.plan()["operations"], [])
        self.assertEqual(self.plan()["reason"], "disabled")

    def test_enabled_still_has_no_execution_adapter(self):
        p = self.plan(ProbeSpec(enabled=True))
        self.assertEqual(p["state"], "plan_only")
        self.assertFalse(p["adapter_present"])
        self.assertFalse(p["hard_latency_bound"])

    def test_trial_budget_and_spacing(self):
        spec = ProbeSpec(enabled=True)
        self.assertEqual(self.plan(spec, trial_index=8)["reason"], "trial_budget_exhausted")
        self.assertEqual(self.plan(spec, previous_start_ns=0, now_ns=10)["reason"], "spacing_budget")
        self.assertEqual(self.plan(spec, previous_start_ns=0, now_ns=300_000_000_000)["state"], "plan_only")

    def test_insufficient_slack_skips(self):
        self.assertEqual(self.plan(ProbeSpec(enabled=True), deadline_slack_ns=1)["reason"], "insufficient_nominal_slack")

    def test_spec_volume_and_rate_limits(self):
        for kw in ({"payload_bytes": 4097}, {"max_trials": 33}, {"payload_bytes": 4096, "max_trials": 9},
                   {"min_spacing_ns": 1}, {"required_slack_ns": 1}, {"enabled": 1}):
            with self.assertRaises(ValueError):
                ProbeSpec(**kw)

    def test_successful_synthetic_transcript_does_not_claim_durability(self):
        r = summarize_transcript(self.stages(), payload_bytes=1024, exact_readback=True)
        self.assertEqual(r["state"], "complete")
        self.assertEqual(r["total_bracket_ns"], 55)
        self.assertEqual(r["stage_durations_ns"]["fsync_file"], 5)
        self.assertFalse(r["crash_durability_demonstrated"])
        self.assertFalse(r["residue_possible"])

    def test_failed_fsync_with_cleanup_preserves_failure(self):
        stages = self.stages()[:2] + [StageResult("fsync_file", 20, 30, "error"),
                                    StageResult("close", 40, 45), StageResult("unlink", 50, 55)]
        r = summarize_transcript(stages, payload_bytes=1024, exact_readback=None)
        self.assertEqual(r["state"], "failed")
        self.assertFalse(r["residue_possible"])
        self.assertEqual(r["stage_outcomes"]["fsync_file"], "error")

    def test_readback_mismatch_is_failed(self):
        r = summarize_transcript(self.stages(), payload_bytes=1024, exact_readback=False)
        self.assertEqual(r["state"], "failed")

    def test_unlinked_file_not_assumed_after_missing_cleanup(self):
        r = summarize_transcript(self.stages()[:4], payload_bytes=1024, exact_readback=True)
        self.assertEqual(r["state"], "incomplete")
        self.assertTrue(r["residue_possible"])

    def test_invalid_order_overlap_and_false_read_claim_rejected(self):
        cases = [([self.stages()[1]], None),
                 ([self.stages()[0], self.stages()[0]], None),
                 ([self.stages()[0], StageResult("write", 4, 6)], None),
                 ([self.stages()[0]], True),
                 ([StageResult("create_exclusive", 0, 1, "error"), StageResult("write", 2, 3)], None)]
        for stages, match in cases:
            with self.assertRaises(ValueError):
                summarize_transcript(stages, payload_bytes=1024, exact_readback=match)

    def test_non_boolean_readback_rejected(self):
        for value in (1, 0, "true", []):
            with self.assertRaises(ValueError):
                summarize_transcript(self.stages(), payload_bytes=1024, exact_readback=value)

    def test_cleanup_after_failed_creation_rejected(self):
        for cleanup in ("close", "unlink"):
            stages = [StageResult("create_exclusive", 0, 1, "error"), StageResult(cleanup, 2, 3)]
            with self.subTest(cleanup=cleanup), self.assertRaisesRegex(ValueError, "cleanup_without_successful_creation"):
                summarize_transcript(stages, payload_bytes=1024, exact_readback=None)

    def test_creation_failure_never_establishes_ownership(self):
        stages = [StageResult("create_exclusive", 0, 1, "error")]
        r = summarize_transcript(stages, payload_bytes=1024, exact_readback=None)
        self.assertEqual(r["state"], "failed")
        self.assertFalse(r["residue_possible"])
        self.assertFalse(r["cleanup_authority_established"])
