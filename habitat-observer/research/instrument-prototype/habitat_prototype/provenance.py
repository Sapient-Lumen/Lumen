"""Public-safe run contracts, terminal-byte reservation, and endpoint evidence."""
from dataclasses import dataclass
import hashlib
import json
import re
from .measurement import integer, identifier


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


@dataclass(frozen=True)
class RunContract:
    run_id: str
    code_sha256: str
    clock_epoch: str
    origin_monotonic_ns: int
    period_ns: int
    duration_ns: int
    log_budget_bytes: int = 8 * 1024 * 1024
    terminal_reserve_bytes: int = 4096
    maximum_record_bytes: int = 32768
    mode: str = "synthetic"

    def __post_init__(self):
        identifier(self.run_id, "run_id")
        identifier(self.clock_epoch, "clock_epoch")
        if not isinstance(self.code_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.code_sha256):
            raise ValueError("invalid_code_hash")
        integer(self.origin_monotonic_ns, "origin")
        for name in ("period_ns", "duration_ns", "log_budget_bytes", "terminal_reserve_bytes", "maximum_record_bytes"):
            integer(getattr(self, name), name, 1)
        if not 1_000_000_000 <= self.period_ns <= 3_600_000_000_000:
            raise ValueError("period_outside_reviewed_bounds")
        if not self.period_ns <= self.duration_ns <= 86_400_000_000_000:
            raise ValueError("duration_outside_reviewed_bounds")
        if not 65536 <= self.log_budget_bytes <= 8 * 1024 * 1024:
            raise ValueError("log_budget_outside_reviewed_bounds")
        if not 1 <= self.terminal_reserve_bytes <= self.maximum_record_bytes <= 32768:
            raise ValueError("invalid_record_reservation")
        if self.mode not in {"synthetic", "passive_review_required"}:
            raise ValueError("unsupported_mode")

    def as_dict(self):
        return {
            "schema": "habitat.instrument-contract.v0-prototype",
            "run_id": self.run_id, "code_sha256": self.code_sha256,
            "clock_epoch": self.clock_epoch, "origin_monotonic_ns": self.origin_monotonic_ns,
            "period_ns": self.period_ns, "duration_ns": self.duration_ns,
            "end_exclusive": True, "deadline_policy": "fixed_lattice_skip_without_backfill",
            "log_budget_bytes": self.log_budget_bytes,
            "terminal_reserve_bytes": self.terminal_reserve_bytes,
            "maximum_record_bytes": self.maximum_record_bytes,
            "mode": self.mode, "active_filesystem_probe_enabled": False,
            "clock_contract": {
                "elapsed": "monotonic_ns within matching caller-assigned epoch only",
                "wall": "realtime_ns used for correspondence and discrepancy diagnostics",
                "cpu": "process_time_ns; same process; all its threads; no child CPU",
            },
            "scope_contract": "allowlisted scalar values; no host IDs, paths, prompts, credentials, or payload bodies",
            "limitations": ["caller must establish epoch identity", "hash is integrity evidence, not authentication",
                            "run contract is separate from the recorder's segment manifest"],
        }

    @property
    def sha256(self):
        return hashlib.sha256(canonical_bytes(self.as_dict())).hexdigest()


class ByteLedger:
    """Admission accounting only. Caller charges exact encoded record bytes.

    ``admit`` reserves bytes before writing and never refunds failed/uncertain
    writes. One small terminal record can use the reserved tail. Segment indexes,
    contracts, temporary files and filesystem metadata need a separate budget.
    """
    def __init__(self, total_bytes, terminal_reserve_bytes, max_record_bytes=32768):
        integer(total_bytes, "total_bytes", 1)
        integer(terminal_reserve_bytes, "terminal_reserve_bytes", 1)
        integer(max_record_bytes, "max_record_bytes", 1)
        if not terminal_reserve_bytes <= max_record_bytes <= total_bytes:
            raise ValueError("invalid_byte_budget")
        self.total = total_bytes
        self.reserve = terminal_reserve_bytes
        self.max_record = max_record_bytes
        self.used = 0
        self.terminal_admitted = False

    def admit(self, encoded_size, *, terminal=False):
        integer(encoded_size, "encoded_size", 1)
        if type(terminal) is not bool:
            raise ValueError("terminal_boolean_required")
        if self.terminal_admitted or encoded_size > self.max_record:
            return False
        cap = self.total if terminal else self.total - self.reserve
        if terminal and encoded_size > self.reserve:
            return False
        if self.used + encoded_size > cap:
            return False
        self.used += encoded_size
        self.terminal_admitted = terminal
        return True


def lifetime_evidence(*, start_ns, last_validated_ns, clock_epoch_matches,
                      terminal_kind=None, terminal_reason=None):
    """Describe a validated recorder prefix without declaring environment death.

    ``terminal_kind`` comes only from the final validated record, never from file
    mtime, an expected duration, a missing process, or absent follow-up evidence.
    """
    integer(start_ns, "start")
    integer(last_validated_ns, "last_validated")
    if type(clock_epoch_matches) is not bool:
        raise ValueError("epoch_evidence_boolean_required")
    if terminal_kind not in {None, "stop"}:
        raise ValueError("invalid_terminal_kind")
    reasons = {None, "duration_complete", "budget_exhausted", "interrupted", "read_error", "write_error", "other_reported_stop"}
    if terminal_reason not in reasons or terminal_kind is None and terminal_reason is not None:
        raise ValueError("invalid_terminal_reason")
    if last_validated_ns < start_ns:
        raise ValueError("negative_recorded_extent")
    status = "nonterminal_retained_prefix"
    if terminal_kind == "stop":
        status = "administrative_end_recorded" if terminal_reason == "duration_complete" else "reported_stop_recorded"
    return {
        "recording_endpoint": status,
        "terminal_reason": terminal_reason,
        "recorded_extent_ns": last_validated_ns - start_ns if clock_epoch_matches else None,
        "clock_epoch_matches": clock_epoch_matches,
        "statistical_censoring_classification": "not_established",
        "environment_birth_observed": False,
        "environment_death_observed": False,
        "environment_lifetime": "not_identified; recording starts after an unknown environment birth and ends without observed death",
        "continuous_availability_proven": False,
        "stop_record_proves_process_exit": False,
        "qualification": "a validated local prefix is evidence of records; silence is not a death event",
        "censoring_qualification": "a retained prefix alone establishes neither a defined observation cutoff nor a maintained observation channel or noninformative censoring",
    }
