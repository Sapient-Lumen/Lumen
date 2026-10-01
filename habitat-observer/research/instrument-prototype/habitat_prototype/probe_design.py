"""A low-volume filesystem probe PLAN and transcript checker, not an executor.

The missing execution adapter is intentional: synchronous fsync has no portable
hard latency bound. Neither enabling the plan nor importing this module writes
anything. Synthetic transcripts establish algebra only, not filesystem claims.
"""
from dataclasses import dataclass
from .measurement import integer

STAGES = ("create_exclusive", "write", "fsync_file", "readback_same_fd", "close", "unlink")


@dataclass(frozen=True)
class ProbeSpec:
    enabled: bool = False
    payload_bytes: int = 1024
    max_trials: int = 8
    min_spacing_ns: int = 300_000_000_000
    required_slack_ns: int = 100_000_000

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise ValueError("enable_boolean_required")
        for name in ("payload_bytes", "max_trials", "min_spacing_ns", "required_slack_ns"):
            integer(getattr(self, name), name, 1)
        if not self.payload_bytes <= 4096 or not self.max_trials <= 32:
            raise ValueError("probe_volume_budget_exceeded")
        if self.payload_bytes * self.max_trials > 32768:
            raise ValueError("probe_total_budget_exceeded")
        if self.min_spacing_ns < 300_000_000_000 or self.required_slack_ns < 100_000_000:
            raise ValueError("probe_rate_or_slack_budget_exceeded")


def plan_trial(spec, *, trial_index, now_ns, previous_start_ns=None, deadline_slack_ns):
    integer(trial_index, "trial_index")
    integer(now_ns, "now")
    integer(deadline_slack_ns, "deadline_slack")
    if previous_start_ns is not None:
        integer(previous_start_ns, "previous_start")
        if previous_start_ns > now_ns:
            raise ValueError("monotonic_regression")
    reason = None
    if not spec.enabled:
        reason = "disabled"
    elif trial_index >= spec.max_trials:
        reason = "trial_budget_exhausted"
    elif previous_start_ns is not None and now_ns - previous_start_ns < spec.min_spacing_ns:
        reason = "spacing_budget"
    elif deadline_slack_ns < spec.required_slack_ns:
        reason = "insufficient_nominal_slack"
    if reason:
        return {"state": "not_scheduled", "reason": reason, "operations": []}
    return {
        "state": "plan_only", "trial_index": trial_index,
        "payload_bytes": spec.payload_bytes, "operations": list(STAGES),
        "adapter_present": False,
        "executor_requirement": "caller-approved, empty private scratch directory; exclusive no-follow relative creation; cleanup only the exact file successfully created and still owned; never unlink an existing path after exclusive creation failed",
        "cleanup_authority": "accepted transcript ordering does not authorize cleanup or establish file identity or ownership",
        "hard_latency_bound": False,
        "nominal_slack_is_timeout_guarantee": False,
        "interpretation": "write and fsync API return plus same-file-descriptor readback; not crash-recovery or physical-media durability",
    }


@dataclass(frozen=True)
class StageResult:
    stage: str
    start_ns: int
    end_ns: int
    outcome: str = "ok"

    def __post_init__(self):
        if self.stage not in STAGES or self.outcome not in {"ok", "error", "unsupported"}:
            raise ValueError("invalid_stage_result")
        integer(self.start_ns, "stage_start")
        integer(self.end_ns, "stage_end")
        if self.end_ns < self.start_ns:
            raise ValueError("negative_stage_duration")


def summarize_transcript(stages, *, payload_bytes, exact_readback, synthetic=True):
    """Accept a successful prefix, optionally followed by cleanup after failure.

    Stage durations come from caller-supplied monotonic brackets. Errors must not
    be silently converted into zero timings or a success. Cleanup is permissible
    only for the exact file the executor successfully created and still owns.
    In particular, exclusive-create failure never authorizes unlinking its path.
    The checker rejects cleanup lacking reported successful creation, but accepted
    ordering is not evidence of real ownership, file identity, or cleanup authority.
    Cleanup failure leaves residue_possible true. At most six records are accepted.
    """
    integer(payload_bytes, "payload_bytes", 1)
    if payload_bytes > 4096 or len(stages) > len(STAGES):
        raise ValueError("transcript_budget_exceeded")
    if exact_readback is not None and type(exact_readback) is not bool or type(synthetic) is not bool:
        raise ValueError("invalid_transcript_flags")
    seen = set()
    last_order = -1
    last_end = None
    failed = False
    created_ok = False
    for item in stages:
        if not isinstance(item, StageResult):
            raise ValueError("typed_stage_required")
        order = STAGES.index(item.stage)
        if item.stage in seen or order <= last_order or last_end is not None and item.start_ns < last_end:
            raise ValueError("invalid_stage_order")
        if not failed and order != last_order + 1:
            raise ValueError("missing_success_stage")
        if failed and item.stage not in {"close", "unlink"}:
            raise ValueError("unsafe_continuation_after_failure")
        if item.stage in {"close", "unlink"} and not created_ok:
            raise ValueError("cleanup_without_successful_creation")
        seen.add(item.stage)
        last_order, last_end = order, item.end_ns
        failed = failed or item.outcome != "ok"
        if item.stage == "create_exclusive":
            created_ok = item.outcome == "ok"
    results = {s.stage: s for s in stages}
    readback_ok = "readback_same_fd" in results and results["readback_same_fd"].outcome == "ok"
    if exact_readback is not None and not readback_ok:
        raise ValueError("readback_claim_without_successful_read")
    complete = len(stages) == len(STAGES) and not failed and exact_readback is True
    created = "create_exclusive" in results and results["create_exclusive"].outcome == "ok"
    cleanup_ok = "unlink" in results and results["unlink"].outcome == "ok"
    return {
        "schema": "habitat.probe-transcript.v0-prototype",
        "synthetic": synthetic, "payload_bytes": payload_bytes,
        "state": "complete" if complete else "failed" if failed or exact_readback is False else "incomplete",
        "exact_readback": exact_readback,
        "stage_durations_ns": {s.stage: s.end_ns - s.start_ns for s in stages},
        "stage_outcomes": {s.stage: s.outcome for s in stages},
        "total_bracket_ns": stages[-1].end_ns - stages[0].start_ns if stages else None,
        "residue_possible": created and not cleanup_ok,
        "crash_durability_demonstrated": False,
        "cleanup_authority_established": False,
        "qualification": "same-FD readback can be served from cache; fsync return does not test recovery",
    }
