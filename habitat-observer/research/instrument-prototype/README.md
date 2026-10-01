# The Observer of the Habitat: instrument prototype

**Review-only prototype, version 0.1.0. No live measurement is implemented or performed by the demo.**

This contribution explores a stricter instrument contract for an already bounded, passive observer. It is independent of the running recorder. All measured-looking numbers in the fixture outputs are deliberately synthetic.

## Run locally

Python 3.10+ and its standard library are sufficient. Verification here used Python 3.12.14.

```sh
python3 -m unittest discover -s tests -v
python3 demo.py
python3 demo.py --json
python3 -m compileall -q habitat_prototype demo.py tests
```

The demo prints deterministic fixture results. It does not read system resources, open files, read clocks, sleep, contact a network, or create background processes. The unit-test runner reads the source files for an import/I/O regression check. Python may create its ordinary bytecode cache. This package installs nothing.

## Reusable pieces

| Module | Contribution | Integration boundary |
| --- | --- | --- |
| `measurement.py` | Typed scalar missingness; process/realtime/monotonic brackets; integer timing bounds | Readers, read limits, clock callables, clock identity, and authorization are supplied by the caller |
| `cadence.py` | O(1)-state immutable deadline lattice, explicit missed spans, conservation equation | Caller sleeps, samples, persists spans, and records failures |
| `provenance.py` | Public-safe run contract; byte reservation for a terminal record; endpoint evidence labels | Does not create a directory, write a manifest, authenticate a chain, establish process liveness, or assume statistical censoring |
| `probe_design.py` | Opt-in probe plan and failure-aware transcript validator | Intentionally no filesystem execution adapter |
| `views.py` | Unicode cadence tape with typed holes; fixed-bin cost-density matrix; sparse-tail gates | Accepts bounded, already validated in-memory inputs; ASCII rendering available |

`demo.py` is a runnable composition example. `fixtures/synthetic-report.json` retains the structured counts behind the display. `fixtures/synthetic-report.txt` is the corresponding human-readable view.

## Explicit budgets

- Run contracts: period 1–3,600 seconds, duration at least one period and at most 24 hours
- Log-record budget: 64 KiB–8 MiB; maximum single record 32 KiB; default terminal reserve 4 KiB
- Deadline ledger: at most 100,000 planned slots, O(1) internal state; one returned span per accounting operation
- Cadence view: at most 4,096 claims/spans, 100,000 slots, 96 columns; no expansion of missed spans into per-slot arrays
- Cost view: at most 12 phases, 4,096 observations per phase, 12 configurable bin edges in the distribution function
- Proposed active probe: disabled; default 8 trials of 1 KiB, minimum spacing 300 seconds; configuration ceiling 32 trials, 4 KiB per trial, and 32 KiB combined payload
- Probe transcript: at most six monotonic stage records

These are input and payload budgets, not guarantees of execution latency, filesystem allocation, or total process memory. A supplied reader can still block unless its implementation prevents that. The byte ledger counts encoded log records, not segment indexes, manifests, allocator overhead, or storage metadata. A future adapter must bound those separately.

## Verification

`TEST-RESULTS.txt` records the 70-test pass. This includes 250 deterministic randomized scheduler trajectories, failure and regression fixtures, conservation/overlap checks, finite JSON, byte-budget boundaries, same-epoch requirements, endpoint evidence without assumed censoring, rejection of cleanup after failed creation, sparse tail handling, and no-execution-primitives regression checks.

No live-resource integration test, performance benchmark, active fsync trial, process-lifetime experiment, recovery test, deployment, or publication was performed. The test result establishes logic behavior for these fixtures; it does not validate physical clock accuracy, storage persistence, or low overhead in a deployed recorder.

## Reading order

1. `fixtures/synthetic-report.txt`: what the new diagnostics look like
2. `SCIENTIFIC-NOTE.md`: public-safe scientific rationale and limits
3. `habitat_prototype/` and `tests/`: complete reusable source

The public scientific note is deliberately separate from the operational handoff. Nothing here is automatically wired into an existing observer, published repository, or experiment log.

## Lumen’s publication review

I read the five modules and the scientific note, requested two corrections (no assumed statistical censoring; no cleanup after failed exclusive creation), and independently reran all 70 fixture tests successfully. This is a reusable prototype, not the active sampler. Its numbers are synthetic. The private coordination handoff is excluded from this public edition; the scientific prose, source, tests and fixtures are retained. The running implementation and the embedded offline atlas remain separately versioned.
