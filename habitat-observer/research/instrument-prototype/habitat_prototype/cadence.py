"""An O(1)-state deadline ledger. Pure arithmetic: never sleeps or samples.

Slots are anchored to origin + k * period and end is exclusive. A delayed wake
may claim the newest due slot; earlier slots become one explicit missed span.
Completing a sample skips deadlines strictly before completion, never backfills.
"""
from dataclasses import dataclass
from .measurement import integer


@dataclass(frozen=True)
class MissedSpan:
    first: int
    stop: int  # exclusive
    reason: str

    def __post_init__(self):
        integer(self.first, "first_slot")
        integer(self.stop, "stop_slot")
        if self.stop <= self.first or self.reason not in {"delayed_wake", "observer_overrun", "unclaimed_at_close"}:
            raise ValueError("invalid_missed_span")

    @property
    def count(self):
        return self.stop - self.first

    def as_dict(self):
        return {"first_slot": self.first, "stop_slot_exclusive": self.stop, "count": self.count, "reason": self.reason}


@dataclass(frozen=True)
class Claim:
    slot: int
    deadline_ns: int
    started_ns: int
    missed_before: object = None

    def __post_init__(self):
        integer(self.slot, "claim_slot")
        integer(self.deadline_ns, "claim_deadline")
        integer(self.started_ns, "claim_start")
        if self.started_ns < self.deadline_ns or self.missed_before is not None and not isinstance(self.missed_before, MissedSpan):
            raise ValueError("invalid_claim")

    @property
    def lateness_ns(self):
        return self.started_ns - self.deadline_ns

    def as_dict(self):
        return {"slot": self.slot, "deadline_ns": self.deadline_ns,
                "started_ns": self.started_ns, "lateness_ns": self.lateness_ns,
                "missed_before": None if self.missed_before is None else self.missed_before.as_dict()}


class DeadlineLedger:
    def __init__(self, origin_ns, period_ns, duration_ns):
        self.origin_ns = integer(origin_ns, "origin")
        self.period_ns = integer(period_ns, "period", 1)
        self.duration_ns = integer(duration_ns, "duration", 1)
        self.total_slots = (duration_ns + period_ns - 1) // period_ns
        if self.total_slots > 100_000:
            raise ValueError("slot_budget_exceeded")
        self.next_slot = self.claimed = self.completed = self.missed = self.late = 0
        self.pending = None
        self.closed = False
        self.last_time_ns = origin_ns

    @property
    def end_ns(self):
        return self.origin_ns + self.duration_ns

    @property
    def next_wake_ns(self):
        if self.closed or self.pending is not None:
            return None
        return min(self.end_ns, self.origin_ns + self.next_slot * self.period_ns)

    def _time(self, now_ns):
        integer(now_ns, "now")
        if now_ns < self.last_time_ns:
            raise ValueError("monotonic_regression")
        self.last_time_ns = now_ns

    def _miss(self, stop, reason):
        stop = min(self.total_slots, stop)
        if stop <= self.next_slot:
            return None
        span = MissedSpan(self.next_slot, stop, reason)
        self.missed += span.count
        self.next_slot = stop
        return span

    def claim(self, now_ns):
        if self.closed or self.pending is not None:
            raise ValueError("ledger_closed_or_sample_pending")
        self._time(now_ns)
        if now_ns >= self.end_ns or self.next_slot >= self.total_slots:
            return None
        newest = (now_ns - self.origin_ns) // self.period_ns
        if newest < self.next_slot:
            return None
        span = self._miss(newest, "delayed_wake")
        claim = Claim(newest, self.origin_ns + newest * self.period_ns, now_ns, span)
        self.next_slot = newest + 1
        self.claimed += 1
        self.late += int(claim.lateness_ns > 0)
        self.pending = claim
        return claim

    def complete(self, now_ns):
        if self.pending is None or self.closed:
            raise ValueError("no_pending_sample")
        self._time(now_ns)
        first_not_earlier = (now_ns - self.origin_ns + self.period_ns - 1) // self.period_ns
        span = self._miss(first_not_earlier, "observer_overrun")
        self.completed += 1
        self.pending = None
        return span

    def close(self, now_ns):
        if self.closed or self.pending is not None:
            raise ValueError("ledger_closed_or_sample_pending")
        self._time(now_ns)
        due_stop = min(self.total_slots, (now_ns - self.origin_ns) // self.period_ns + 1)
        span = self._miss(due_stop, "unclaimed_at_close")
        self.closed = True
        return span

    def summary(self):
        return {"planned_slots": self.total_slots, "claimed_slots": self.claimed,
                "completed_slots": self.completed, "late_claims": self.late,
                "missed_slots": self.missed, "remaining_slots": self.total_slots - self.next_slot,
                "pending_sample": self.pending is not None, "closed": self.closed,
                "conservation_holds": self.claimed + self.missed + self.total_slots - self.next_slot == self.total_slots}
