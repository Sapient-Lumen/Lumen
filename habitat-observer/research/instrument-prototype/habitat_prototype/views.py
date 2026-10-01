"""Bounded Unicode diagnostics whose missingness survives visual compression."""
from collections import Counter
import bisect
import math
from .cadence import Claim, MissedSpan
from .measurement import Quantity, State, Unit, identifier, integer

GLYPHS = {"on_time": "●", "late": "◔", "missed": "×", "unknown": "?", "future": "·", "mixed": "◆"}
ASCII = {"on_time": "o", "late": "l", "missed": "x", "unknown": "?", "future": ".", "mixed": "+"}


def cadence_projection(total_slots, claims, missed_spans, *, elapsed_slots, width=64, ascii_only=False):
    integer(total_slots, "total_slots", 1)
    integer(elapsed_slots, "elapsed_slots")
    integer(width, "width", 1)
    if total_slots > 100_000 or elapsed_slots > total_slots or width > 96:
        raise ValueError("projection_budget_or_horizon_invalid")
    if len(claims) + len(missed_spans) > 4096:
        raise ValueError("projection_record_budget_exceeded")
    ranges = []
    for claim in claims:
        if not isinstance(claim, Claim) or claim.slot < 0 or claim.lateness_ns < 0:
            raise ValueError("invalid_claim")
        ranges.append((claim.slot, claim.slot + 1, "late" if claim.lateness_ns else "on_time"))
    for span in missed_spans:
        if not isinstance(span, MissedSpan):
            raise ValueError("typed_missed_span_required")
        ranges.append((span.first, span.stop, "missed"))
    ranges.sort()
    previous_stop = 0
    for first, stop, state in ranges:
        if first < previous_stop or stop > elapsed_slots:
            raise ValueError("overlapping_or_future_evidence")
        previous_stop = stop
    width = min(width, total_slots)
    alphabet = ASCII if ascii_only else GLYPHS
    bins, glyphs, totals = [], [], Counter()
    for column in range(width):
        first, stop = column * total_slots // width, (column + 1) * total_slots // width
        counts = Counter()
        for lo, hi, state in ranges:
            overlap = max(0, min(stop, hi) - max(first, lo))
            if overlap:
                counts[state] += overlap
        due_count = max(0, min(stop, elapsed_slots) - first)
        covered_count = sum(counts.values())
        if due_count > covered_count:
            counts["unknown"] = due_count - covered_count
        future_count = stop - first - due_count
        if future_count:
            counts["future"] = future_count
        state = next(iter(counts)) if len(counts) == 1 else "mixed"
        glyphs.append(alphabet[state])
        bins.append({"first_slot": first, "stop_slot_exclusive": stop, "state": state, "counts": dict(counts)})
        totals.update(counts)
    return {"glyphs": "".join(glyphs), "bins": bins, "counts": dict(totals),
            "total_slots": total_slots, "columns": width,
            "qualification": "each column is a slot range; mixed columns retain exact counts; no gap interpolation"}


def render_cadence(projection, *, ascii_only=False):
    g = ASCII if ascii_only else GLYPHS
    counts = projection["counts"]
    count_text = ", ".join(f"{name}={counts.get(name, 0)}" for name in ("on_time", "late", "missed", "unknown", "future"))
    return "\n".join([
        f"CADENCE | slot 0 to {projection['total_slots'] - 1}; {projection['columns']} columns",
        "[" + projection["glyphs"] + "]", count_text,
        "  ".join(f"{g[k]} {k.replace('_', ' ')}" for k in GLYPHS),
    ])


def nearest_rank(values, percentile, *, minimum_count):
    """A transparent descriptive statistic; no confidence-interval claim."""
    if not values or len(values) < minimum_count:
        return None
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def cost_distribution(observations, *, edges_ns=(100_000, 1_000_000, 10_000_000, 100_000_000, 1_000_000_000)):
    if len(observations) > 4096 or not 1 <= len(edges_ns) <= 12:
        raise ValueError("distribution_budget_exceeded")
    for edge in edges_ns:
        integer(edge, "bin_edge", 1)
    if sorted(set(edges_ns)) != list(edges_ns):
        raise ValueError("strictly_increasing_edges_required")
    values, missing, scopes = [], Counter(), set()
    for observation in observations:
        if not isinstance(observation, Quantity) or observation.unit is not Unit.NANOSECONDS:
            raise ValueError("typed_nanosecond_quantity_required")
        scopes.add(observation.scope)
        if observation.state is State.OBSERVED:
            values.append(observation.value)
        else:
            missing[observation.state.value] += 1
    if len(scopes) > 1:
        raise ValueError("mixed_measurement_scopes")
    counts = [0] * (len(edges_ns) + 1)
    for value in values:
        counts[bisect.bisect_right(edges_ns, value)] += 1
    return {
        "edges_ns": list(edges_ns), "bin_counts": counts, "observed_count": len(values),
        "scope": next(iter(scopes)).value if scopes else None,
        "missing_by_state": dict(missing),
        "minimum_ns": min(values) if values else None, "maximum_ns": max(values) if values else None,
        "p50_ns": nearest_rank(values, .50, minimum_count=1),
        "p95_ns": nearest_rank(values, .95, minimum_count=20),
        "p99_ns": nearest_rank(values, .99, minimum_count=100),
        "quantile_policy": "nearest rank; p95 withheld below 20, p99 below 100; gates do not establish tail precision",
    }


def render_cost_matrix(phases, *, ascii_only=False):
    """Fixed edge matrix: darker cells mean larger counts, never longer latency."""
    if not 1 <= len(phases) <= 12:
        raise ValueError("phase_budget_exceeded")
    for phase in phases:
        identifier(phase, "phase")
    distributions = {name: cost_distribution(values) for name, values in phases.items()}
    ramp = " .:+#" if ascii_only else " ·░▒▓"
    largest = max((count for d in distributions.values() for count in d["bin_counts"]), default=0)
    lines = ["COST DENSITY | fixed elapsed-time bins; cell darkness = count",
             "phase            <0.1ms  <1ms   <10ms  <100ms  <1s    >=1s   n"]
    for phase, d in distributions.items():
        cells = []
        for count in d["bin_counts"]:
            index = 0 if count == 0 else max(1, math.ceil(4 * count / largest))
            cells.append(f"{ramp[index]}{count:<5}")
        lines.append(f"{phase[:16]:16} " + " ".join(cells) + f" {d['observed_count']}")
        if d["missing_by_state"]:
            lines.append("  excluded, retained as states: " + ", ".join(f"{k}={v}" for k, v in sorted(d["missing_by_state"].items())))
    lines.append("Bins are [previous edge, next edge); the first includes zero. ASCII mode is available.")
    lines.append("Sparse tails are not estimated: p95 requires n>=20; p99 requires n>=100.")
    return "\n".join(lines)
