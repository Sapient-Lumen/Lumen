#!/usr/bin/env python3
"""Print deterministic synthetic diagnostics. Does not sample the environment."""
import argparse
import json
from habitat_prototype.cadence import DeadlineLedger
from habitat_prototype.measurement import ClockStamp, Quantity, Scope, State, Unit, paired_interval
from habitat_prototype.provenance import RunContract, lifetime_evidence
from habitat_prototype.probe_design import ProbeSpec, StageResult, STAGES, plan_trial, summarize_transcript
from habitat_prototype.views import cadence_projection, cost_distribution, render_cadence, render_cost_matrix

SECOND = 1_000_000_000


def fixture():
    ledger = DeadlineLedger(0, 10 * SECOND, 120 * SECOND)
    claims, spans = [], []
    # 0 -> 26: slots 1 and 2 are lost to collection. Wake at 47: slot 3 was missed.
    for start, finish in ((0, 26), (47, 48), (50, 51), (60, 61), (91, 112)):
        claim = ledger.claim(start * SECOND)
        claims.append(claim)
        if claim.missed_before:
            spans.append(claim.missed_before)
        span = ledger.complete(finish * SECOND)
        if span:
            spans.append(span)
    span = ledger.close(120 * SECOND)
    if span:
        spans.append(span)
    projection = cadence_projection(ledger.total_slots, claims, spans, elapsed_slots=12, width=12)
    phases = {
        "resource_read": [Quantity(State.OBSERVED, Unit.NANOSECONDS, Scope.SYNTHETIC, n) for n in (40_000, 90_000, 100_000, 350_000, 900_000, 1_100_000)],
        "record_commit": [Quantity(State.OBSERVED, Unit.NANOSECONDS, Scope.SYNTHETIC, n) for n in (900_000, 2_000_000, 6_000_000, 90_000_000, 1_200_000_000)],
    }
    phases["resource_read"].append(Quantity(State.DENIED, Unit.NANOSECONDS, Scope.SYNTHETIC))
    contract = RunContract("synthetic-example", "0" * 64, "fixture-epoch", 0, 10 * SECOND, 120 * SECOND)
    stages = [StageResult(stage, i * 1_000_000, i * 1_000_000 + 100_000) for i, stage in enumerate(STAGES)]
    summary = {
        "synthetic": True,
        "contract": contract.as_dict(), "contract_sha256": contract.sha256,
        "cadence": ledger.summary(), "claims": [c.as_dict() for c in claims],
        "missed_spans": [s.as_dict() for s in spans], "cadence_projection": projection,
        "cost_distributions": {name: cost_distribution(values) for name, values in phases.items()},
        "clock_example": paired_interval(ClockStamp(0, 10 * SECOND, 0, 100, "fixture"),
                                         ClockStamp(SECOND, 9 * SECOND, 20_000_000, SECOND + 100, "fixture")),
        "lifetime": lifetime_evidence(start_ns=0, last_validated_ns=112 * SECOND, clock_epoch_matches=True),
        "probe_default": plan_trial(ProbeSpec(), trial_index=0, now_ns=0, deadline_slack_ns=SECOND),
        "probe_transcript": summarize_transcript(stages, payload_bytes=1024, exact_readback=True),
    }
    view = "\n\n".join([
        "THE OBSERVER OF THE HABITAT\nInstrument prototype • SYNTHETIC FIXTURES ONLY • no live measurements",
        render_cadence(projection), render_cost_matrix(phases),
        "CLOCK CORRESPONDENCE\nMonotonic: +1 s   Realtime: -1 s   Residual: -2 s\nA discrepancy is observable; its cause is not identified. No negative elapsed duration is emitted.",
        "LIFETIME EVIDENCE\nRecorded extent: 112 s   Endpoint: nonterminal retained prefix\nEnvironment birth: unobserved   Environment death: unobserved\nStatistical censoring: not established by a retained prefix alone\nNo terminal record is not proof of process death. Missing samples remain missing.",
        "PROBE STATUS\nDisabled by default. Synthetic transcript only; no execution adapter.\nSame-FD readback and fsync acknowledgment do not demonstrate crash recovery.",
    ]) + "\n"
    return summary, view


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary, view = fixture()
    print(json.dumps(summary, indent=2, allow_nan=False) if args.json else view, end="\n" if args.json else "")
