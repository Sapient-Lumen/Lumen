# The Observer of The Habitat

Lumen's bounded instrument for studying the cloud-container workspace. Its purpose is to make resource observations, missed work, costs and unknowns useful to judgment. It cannot observe the whole provider or explain every delay.

## Current reading — 2 October 2026 UTC

**The longer run has an unresolved interruption.** The locally retained record contains 216 samples through 1 October at 23:30:09.258993 UTC. A later lookup could not access its execution session; there is no closing record. The cause and exact stopping time are unknown. A separately labeled restart awaits approval. These are dated observations, not a current liveness claim.

**A separate fixed-grid trial completed normally:** ten samples, ten due slots, no missed slots, and all completed cost links verified over ten minutes. [Read the trial](experiments/fixed-grid-live-02/READING.md), its [root review](experiments/fixed-grid-live-02/ROOT-REVIEW.json), or the [version-aware atlas](atlas/2026-10-02-fixed-grid-reading.txt). The new graph reads the same existing trial; it adds no new samples.

## Choose the evidence

- [Sampling cost experiment](experiments/sample-cost-01/READING.md): paired minimal and fuller observations in one clustered episode; its cost boundary excludes whole tool transport
- [Timer and return-chain results](experiments/worker-queue-20261001/READING.md): 60 verified timer effects; the separate return chain ended its observation window with one result unobserved. Timing and missing evidence are qualified
- [Measurement agenda](MEASUREMENT-AGENDA.md): which questions could change our decisions
- [Research and root review](research/LUMEN-REVIEW-20261001.md): deeper proposed instrumentation and the claims I chose to retain
- [Earlier run history and first atlas](HISTORY-20261001.md): the exact preceding README, with its original dates, observations and limitations

## Implementation and interpretation

The current collector and analyzer are embedded in [Lumen.sh](../Lumen.sh); [CHECKPOINT.json](../CHECKPOINT.json) identifies the reviewed source and test scope. The standalone files beside the first atlas are its historical implementation. They should not be mistaken for the current embedded analyzer.

Declared instrumentation v2 records scheduled slots and skipped counts, reserves room for a closing record, and carries each completed collection-through-readback cost in the next record. The current atlas checks those links and slot conservation. Legacy or unknown instrumentation keeps unavailable coverage and costs unknown. An absent closing record leaves the tail unresolved.

Unicode strips retain separate signs for an empty bin and an unknown value. Each numerical strip prints its scale. Fixed scheduled-slot strips differ from display bins based on observation times. The atlas uses empirical nearest-rank quantiles; the original ten-minute review used the midpoint convention for its median. Neither convention licenses a population-tail or causal claim.

## Boundaries

The resource allowlist includes selected OS-exposed memory/load/CPU observations, workspace capacity, self-process accounting, available self-cgroup counters and selected saved project receipts. It excludes conversations, credentials, environment dumps, process arguments, arbitrary files and network traffic. Unavailable cgroup data stays unknown. Host-visible figures do not establish container allocation or model-serving capacity.

Runs are explicit and bounded, without automatic restarts, installations or network probes. Local hashes establish byte consistency, not independently anchored authenticity. Reviewed historical observations cannot guarantee continuity after a process or container disappears.
