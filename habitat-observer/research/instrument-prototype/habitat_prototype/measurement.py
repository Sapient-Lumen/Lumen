"""Typed scalar observations and injected, paired clock brackets.

No clock is read unless a caller invokes ``stamp`` with supplied clock functions.
This module has no filesystem, network, subprocess, or scheduling code.
"""
from dataclasses import dataclass
from enum import Enum
import errno
import math
import re
from typing import Callable, Optional, Union

Number = Union[int, float]


class State(str, Enum):
    OBSERVED = "observed"
    UNLIMITED = "unlimited"
    UNAVAILABLE = "unavailable"
    DENIED = "permission_denied"
    UNSUPPORTED = "unsupported"
    MALFORMED = "malformed"
    TRANSIENT = "transient_error"
    NOT_SAMPLED = "not_sampled"
    COUNTER_RESET = "counter_reset"


class Unit(str, Enum):
    NANOSECONDS = "ns"
    BYTES = "bytes"
    COUNT = "count"
    RATIO = "ratio"


class Scope(str, Enum):
    PROCESS = "observer_process"
    CGROUP = "self_cgroup"
    OS = "os_exposed"
    FILESYSTEM = "selected_filesystem"
    SYNTHETIC = "synthetic_fixture"


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid_" + name)
    return value


def identifier(value, name="identifier"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise ValueError("invalid_" + name)
    return value


@dataclass(frozen=True)
class Quantity:
    state: State
    unit: Unit
    scope: Scope
    value: Optional[Number] = None

    def __post_init__(self):
        if not isinstance(self.state, State) or not isinstance(self.unit, Unit) or not isinstance(self.scope, Scope):
            raise ValueError("typed_state_unit_scope_required")
        if self.state is State.OBSERVED:
            if type(self.value) not in (int, float) or not math.isfinite(self.value) or self.value < 0:
                raise ValueError("finite_nonnegative_observation_required")
        elif self.value is not None:
            raise ValueError("nonobserved_value_must_be_absent")

    def as_dict(self):
        out = {"state": self.state.value, "unit": self.unit.value, "scope": self.scope.value}
        if self.state is State.OBSERVED:
            out["value"] = self.value
        return out


def parse_nonnegative_integer(raw: str) -> int:
    if not isinstance(raw, str) or len(raw) > 128:
        raise ValueError("invalid_integer_text")
    value = raw.strip()
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("invalid_integer_text")
    return int(value)


def parse_limit(raw, unit=Unit.BYTES, scope=Scope.CGROUP):
    if isinstance(raw, str) and raw.strip() == "max":
        return Quantity(State.UNLIMITED, unit, scope)
    return Quantity(State.OBSERVED, unit, scope, parse_nonnegative_integer(raw))


def exception_state(error):
    # Messages/paths are deliberately excluded. Programmer errors are not hidden.
    if isinstance(error, PermissionError):
        return State.DENIED
    if isinstance(error, FileNotFoundError):
        return State.UNAVAILABLE
    if isinstance(error, NotImplementedError):
        return State.UNSUPPORTED
    if isinstance(error, (ValueError, UnicodeError)):
        return State.MALFORMED
    if isinstance(error, OSError):
        if error.errno in {errno.ENOSYS, errno.ENOTSUP}:
            return State.UNSUPPORTED
        return State.TRANSIENT
    raise error


def capture(reader: Callable[[], str], *, unit: Unit, scope: Scope, limit=False):
    """The caller owns read-size limits and permission; this function does no reading."""
    try:
        raw = reader()
        if limit:
            return parse_limit(raw, unit, scope)
        return Quantity(State.OBSERVED, unit, scope, parse_nonnegative_integer(raw))
    except (OSError, ValueError, NotImplementedError) as error:
        return Quantity(exception_state(error), unit, scope)


@dataclass(frozen=True)
class ClockStamp:
    monotonic_before_ns: int
    realtime_ns: int
    process_cpu_ns: int
    monotonic_after_ns: int
    epoch: str

    def __post_init__(self):
        for name in ("monotonic_before_ns", "realtime_ns", "process_cpu_ns", "monotonic_after_ns"):
            integer(getattr(self, name), name)
        identifier(self.epoch, "clock_epoch")
        if self.monotonic_after_ns < self.monotonic_before_ns:
            raise ValueError("monotonic_regression_in_bracket")


def stamp(monotonic: Callable[[], int], realtime: Callable[[], int], process_cpu: Callable[[], int], *, epoch: str):
    """Bracket both other readings using a supplied monotonic clock; no defaults."""
    before = monotonic()
    wall = realtime()
    cpu = process_cpu()
    after = monotonic()
    return ClockStamp(before, wall, cpu, after, epoch)


def paired_interval(start: ClockStamp, end: ClockStamp, *, jump_tolerance_ns=1_000_000):
    integer(jump_tolerance_ns, "jump_tolerance")
    if start.epoch != end.epoch:
        raise ValueError("clock_epoch_mismatch")
    if end.monotonic_before_ns < start.monotonic_after_ns:
        raise ValueError("overlapping_or_regressing_brackets")
    lo = end.monotonic_before_ns - start.monotonic_after_ns
    hi = end.monotonic_after_ns - start.monotonic_before_ns
    # Retain doubled integers until display: no nanosecond precision loss in large epochs.
    midpoint_twice = lo + hi
    wall_delta = end.realtime_ns - start.realtime_ns
    residual_twice = 2 * wall_delta - midpoint_twice
    uncertainty_twice = hi - lo
    cpu = end.process_cpu_ns - start.process_cpu_ns
    out = {
        "elapsed_ns": {"lower": lo, "upper": hi, "midpoint_twice": midpoint_twice},
        "realtime_delta_ns": wall_delta,
        "clock_residual_ns_twice": residual_twice,
        "bracket_uncertainty_ns_twice": uncertainty_twice,
        "clock_discrepancy": abs(residual_twice) > 2 * jump_tolerance_ns + uncertainty_twice,
        "process_cpu": Quantity(State.OBSERVED if cpu >= 0 else State.COUNTER_RESET,
                                Unit.NANOSECONDS, Scope.PROCESS, cpu if cpu >= 0 else None).as_dict(),
        "cpu_per_elapsed": {"state": "not_identifiable"},
    }
    if cpu >= 0 and lo > 0:
        out["cpu_per_elapsed"] = {"state": "bounded", "lower": cpu / hi, "upper": cpu / lo}
    # A ratio above 1 is retained: process CPU can include simultaneous threads.
    return out
