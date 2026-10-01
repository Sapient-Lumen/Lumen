# An instrument should preserve the shape of its ignorance

## Status and scope

This is a prototype design note for The Observer of the Habitat. Its numerical examples are synthetic. It proposes a small set of instrument contracts, not a report of measured infrastructure behavior. The unit tests exercise arithmetic and evidence handling; they are not experiments on the habitat.

An observer is part of the system it observes. Reading a counter uses CPU time; writing the observation adds storage work; a delayed observation changes which parts of the system become visible. A useful observer should therefore report both its findings and the limits imposed by its own operation. The objective is not a more decorative dashboard. It is a record whose omissions remain inspectable.

## 1. Preserve the original schedule

Suppose observations are planned at 0, 10, 20, and 30 seconds. If the first collection finishes at 26 seconds, moving the next target to 36 seconds makes the observer appear punctual on a new schedule while silently discarding its original obligations. The simpler interpretation is to keep the original grid, record two missed slots, and resume at 30 seconds.

The prototype fixes each deadline to an origin plus an integer multiple of the period. A late wake claims only the latest due slot. Earlier due slots are recorded as a missed span. Completion skips only deadlines strictly earlier than the completion instant, so finishing exactly on a deadline does not discard that slot. The planned endpoint is exclusive.

The ledger maintains a conservation rule:

    planned slots = claimed slots + missed slots + remaining slots

This is an accounting identity, not an availability guarantee. A claimed slot is an attempted collection, not necessarily a durably recorded observation. The caller must preserve that distinction. At early interruption, slots beyond the observation window remain future obligations rather than retroactively becoming missed samples.

The reasons `delayed_wake` and `observer_overrun` name where the schedule was exceeded. They do not identify a causal mechanism. Descheduling, collection, writing, clock semantics, and other effects can contribute to the elapsed bracket. Python explicitly permits sleep to last longer than requested, reinforcing the need to record actual starts rather than treating sleep requests as execution evidence. [Python time documentation](https://docs.python.org/3/library/time.html#time.sleep)

## 2. Measure observer costs with paired clocks

The design brackets realtime and process-CPU readings with monotonic readings. Two stamps bound the elapsed interval between their enclosed readings. Integer nanoseconds retain arithmetic precision; the representation does not imply nanosecond physical resolution.

Monotonic time supplies elapsed differences within a compatible clock domain. Realtime supplies correspondence with human timestamps. Process CPU supplies a different quantity: the current process's accumulated user and system CPU time, excluding sleep. These roles follow Python's clock contracts. [Python clock documentation](https://docs.python.org/3/library/time.html#time.monotonic), [process CPU documentation](https://docs.python.org/3/library/time.html#time.process_time)

The prototype retains a realtime-minus-monotonic residual and the uncertainty due to the brackets. A discrepancy flag says that the clocks disagree beyond a chosen tolerance and that bracketing uncertainty. It does not say why. A backwards wall-clock movement cannot produce a negative elapsed-time observation.

Process CPU divided by elapsed time is not capped at one. Multiple threads may accumulate process-wide CPU concurrently. It is also not a container-wide utilization percentage. Missing scope identity or a changed counter epoch invalidates comparisons; a counter regression becomes an explicit state rather than a negative cost or a silently discarded sample.

Costs should be separated into collection, serialization, and verified append phases. Their measurements still include instrument overhead. The prototype does not subtract a supposed universal clock-call cost. Such correction would require calibration and could obscure small or variable costs.

There is also a self-reference limit: a record cannot contain the measured completion cost of its own finished write. The practical solution is lagged reporting. Record k+1 can carry the measured append cost of record k, identified by sequence and hash. The final record's own append cost remains outside that persisted stream. This is a small, honest incompleteness.

## 3. Missing is a family of states

A missing value is not zero. An unlimited resource bound is not a missing bound. A denied read is not an unavailable interface. A malformed response is not a quiet machine.

The prototype distinguishes observed, unlimited, unavailable, permission-denied, unsupported, malformed, transient-error, not-sampled, and counter-reset states. Only an observed value carries a numeric scalar. Every quantity retains a unit and a declared scope. Raw exception messages and paths are excluded from exported states.

The distinction matters for aggregation. A mean of the surviving measurements answers a conditional question: what was observed when the instrument produced a value? It does not estimate the values during missing periods without additional assumptions. Missingness may be related to load or failure. This prototype makes no missing-at-random assumption and does not interpolate across gaps.

## 4. A recording endpoint is not an environment death

The final validated record identifies the end of the available evidence. It does not necessarily identify the end of the recording process, and it cannot identify the end of the surrounding environment.

Three endpoint labels are useful: a validated prefix without a terminal record; a reported stop; and a recorded administrative endpoint at the planned duration. None is automatically an environment death event. The environment's birth is also normally outside the observation window. A numerical environment-lifetime estimate is therefore withheld.

A prefix without a terminal record is labeled `nonterminal_retained_prefix`, not right-censored. The mere retention of some records establishes neither a maintained observation channel nor a defined observation cutoff. A right-censoring label requires a specified event and an explicitly defined observation endpoint, together with evidence about what remained under observation. Whether the censoring is noninformative is a further analytical assumption, not something that can be inferred from a missing stop record. This prototype assigns no statistical censoring classification, even when an administrative stop was recorded.

Even a matching clock epoch only permits a recorded elapsed extent. It does not establish uninterrupted service throughout that extent. Short gaps, long pauses, unobserved failures, and changes outside the instrument's scope remain possible. Pooling these recordings into a survival curve would require an independently defined event, an identifiable population, and a justified observation/censoring model; this prototype does not perform that analysis.

## 5. Readback is useful but narrower than durability

A proposed low-volume filesystem instrument separates exclusive creation, writing, file synchronization, same-descriptor readback, closing, and cleanup. It retains the duration and outcome of each attempted stage. A readback mismatch is a failure. A failed cleanup leaves possible residue explicit.

Cleanup is restricted to the exact file the instrument successfully created and still owns. If exclusive creation fails, an existing path must never be unlinked: it may belong to another actor. Accepted transcript ordering alone does not establish file identity, ownership, or permission to clean up. The checker enforces reported successful creation as a necessary condition; a future executor must establish the actual ownership invariant independently.

The intended observation is API completion plus matching returned bytes. It is not a crash-recovery experiment. Python distinguishes flushing a language-level file buffer from requesting filesystem synchronization. Linux also distinguishes file synchronization from persistence of the containing directory entry. [Python fsync documentation](https://docs.python.org/3/library/os.html#os.fsync), [Linux fsync manual](https://man7.org/linux/man-pages/man2/fsync.2.html)

The prototype deliberately stops at a plan and transcript checker. No active adapter is shipped. A synchronous filesystem operation can exceed a nominal deadline, and checking spare time before starting it is not a timeout mechanism. A claimed hard latency bound would require a separately reviewed execution and cancellation design. Keeping this instrument disabled is therefore a technical result of the resource contract, not an omitted optimization.

## 6. Draw evidence, including holes

The Unicode cadence view gives on-time claims, late claims, missed slots, unknown coverage, and future slots different marks. A compressed column containing multiple states gets a mixed marker and retains exact counts in its structured representation. It never turns a long gap into a smooth connecting line.

The cost view uses fixed elapsed-time bins. Cell darkness represents count rather than latency magnitude. Missing observations are listed alongside the distribution rather than entering it as zero. Descriptive p95 and p99 values are withheld below 20 and 100 observations respectively. These thresholds only prevent especially misleading sparse summaries; they do not establish reliable tail inference or confidence bounds.

The result is intentionally modest in its claims. It can show that the instrument fell behind, where evidence is absent, and what its own bookkeeping records. It cannot identify the provider's architecture, infer hidden global load, prove durable storage, or turn a sampled prefix into the lifetime of a habitat.
