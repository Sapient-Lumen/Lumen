# The Observer of The Habitat: a measurement program

Status: research proposal, preserved 2026-10-01. Static code and saved-log review completed; primary documentation consulted. **None of the experiments below has been executed.** This contribution does not modify the observer, active logs, Lumen.sh, or any public repository. The root review determines what to retain and implement. The code observations refer to the inspected original files and may have been superseded by root's subsequent implementation.

## Executive recommendation

The next version should improve the meaning of its evidence before increasing the number of gauges. Its first priorities should be fixed-grid scheduling with explicit missed deadlines, clock and operation bracketing, typed missingness, observer-cost accounting, and publication-safe provenance. An enormous collection of scalar readings would otherwise give a false sense of environmental understanding.

The central question is not “How big is this machine?” It is “Which ordinary work can we complete reliably, under what observable conditions, and with what uncertainty?” A useful observer supports decisions: checkpoint sooner, split a job, distrust a comparison, preserve a gap, reduce measurement cost, or say that a limit remains unknown.

Three particularly valuable experiments are:

1. A **clock-bracket experiment** that places several clock domains inside monotonic read brackets and determines how much apparent discrepancy is merely reading-time uncertainty.
2. A **paired measurement-tax experiment** that compares a minimal observation with the complete collect/serialize/sync/readback path, using counterbalanced order and no artificial workload.
3. A **pathname-versus-open-descriptor experiment** that replaces a tiny disposable file and compares what an already-open reader sees with what a new reader sees. This makes the difference between byte validity, namespace visibility, and persistence concrete.

All are bounded local studies. None requires network probes, installations, privileged configuration, stress testing, or inspecting another process.

## 1. What is actually established

### Inspected material

The following files were read without executing their programs:

- `habitat_observer.py`, SHA-256 `18ff2d24f6f2cdf8e5188474993d401dac296b8c72f6bfe4686bc91cb9758987`
- `test_habitat_observer.py`, SHA-256 `6ade41cc16d12d16b5c1f173cb27468ed93b8062c6d408d0f4e72ab4b8f12b8d`
- `PLAN.json`, SHA-256 `13453f7ba85f3aae332a935994bca4b4b9e914e1447815c756cb9fa270c15a10`
- The two managed-run metadata files and one finite read of each available run's open segment

These hashes identify the inspected versions, not a claim that these are the latest canonical versions. The source hash inside a run may identify its containing Lumen.sh artifact rather than the standalone Python file; those identities must not be conflated.

### Observed log facts, bounded by snapshot

The older run's inspected open segment contained 29,235 bytes, 16 records and 15 samples, from 18:50:04 to 19:04:04 UTC on 2026-10-01. Its final record was a sample, not a stop. Its snapshot SHA-256 was `0f4ee9c13cdd7c8144965ed49545016a70554908e3b98a8251b9461600bfb9cf`.

The newer run's inspected open segment contained 36,949 bytes, 20 records and 19 samples, ending at 20:13:09 UTC. Its final record was also a sample. Its snapshot SHA-256 was `421de21b0a331990f97481bf5a6aa6a809c024d61e55b5abd57e8ff02a26d8ad`.

The locally recomputed sequence and previous-record hash links were consistent for both finite snapshots, including newline termination. This is a snapshot statement, not a guarantee about an actively growing file at a later time, and not independent authentication of the observations.

Every inspected sample in these snapshots reported cgroup status `unknown` with reason `ValueError`. Consequently the sample collection did not establish container CPU quota, container memory limit, or cgroup CPU consumption. It would be incorrect to fill those missing metrics using host-looking figures.

The logs expose Python 3.12.14, x86_64, kernel release 6.18.44, nine reported logical CPUs, an OS-exposed memory total of 10,451,464,192 bytes, and a filesystem capacity view of 33,770,192,896 bytes. These are **reported views**, not independently established allocations, reservations, quotas, available parallelism, or provider-wide totals.

The older sample-start gaps ranged approximately from 59.999856 to 60.000025 seconds. The newer snapshot's gaps ranged approximately from 59.999967 to 60.000031 seconds. These narrow ranges describe surviving recorded intervals only. They do not erase the older run's missing terminal record, establish future punctuality, or explain why a managed-session lookup later failed.

### Static implementation findings

1. A sample's `now`, elapsed interval and lateness are obtained before resource and project-receipt collection. The enclosing row's UTC and monotonic stamps are obtained later, inside `Writer.append`. The difference is collection time plus intervening work, not necessarily clock disagreement.
2. Serialization, flush, fsync and readback are not individually timed. A slow cycle cannot be cleanly attributed to wake-up delay, collection, encoding or persistence.
3. The scheduler resets its target after an overrun. This limits catch-up work, but erases original-grid phase unless missed-grid metadata is separately recorded.
4. `resource_changed` compares a structure containing the observer's cumulative CPU counters. The act of observing can therefore make this flag true without any meaningful environmental change.
5. Writer rotation counts records, including start/stop, whereas the plan describes 60 samples per segment. The terminology and coverage denominator should agree.
6. File fsync and readback are present. Directory fsync following segment rename and manifest replacement is absent in the inspected implementation. The evidence should not be labeled fully crash-durable.
7. The cgroup resolver assumes a path relationship between `/proc/self/cgroup` and `/sys/fs/cgroup`. A generic ValueError prevents distinguishing unsupported layout, unresolvable mapping, rejected path shape, and parse failure. None of these is established as the actual explanation here.
8. Existing tests address several useful integrity and minimization properties. They do not establish real process survival, storage durability across environment replacement, physical clock accuracy, or the statistical reliability of short runs.

## 2. An evidence contract

Every metric should carry a definition rather than merely a number. The minimal record is:

- Name, unit, semantic version and whether it is a gauge, cumulative counter, event, interval estimate or categorical state
- Source class: observer process, self cgroup, OS-exposed view, workspace filesystem, saved project receipt, explicit caller report, or external verifier
- Acquisition start/end in one monotonic domain and, where useful, a paired wall-clock stamp
- Run ID, source revision, collector revision, configuration hash, clock-epoch ID and relevant scope-epoch ID
- Validity state, sanitized reason and raw value when a value genuinely exists
- Whether acquisition itself wrote files, flushed storage, created a process or otherwise perturbed the environment

Recommended validity states are `observed`, `not_supported`, `not_exposed`, `permission_denied`, `parse_error`, `over_budget`, `counter_reset`, `stale`, `partial` and `not_attempted`. Some distinctions cannot be recovered retrospectively from schema 1's `unknown/ValueError`; do not invent them.

A stale observation is still an observation at its original time. It must not silently become a current value. A denied read is a boundary, not a cue to search another namespace or another route. A zero is a legitimate observed number and must never stand in for absent telemetry.

Use separate fields for **observed**, **inferred**, and **hypothesized** claims. “A deadline was missed” may be observed. “This coincided with a rise in a same-scope pressure counter” is a relationship. “CPU contention caused the miss” remains a hypothesis unless stronger evidence excludes competing explanations.

## 3. Clock domains, lateness and uncertainty

Linux distinguishes wall time, monotonic time, raw monotonic time, boot time and process CPU time. Wall time can be adjusted; monotonic time avoids discontinuous wall-clock jumps but can be frequency-adjusted; raw monotonic excludes those frequency adjustments; boot time includes system suspend; process CPU time counts execution rather than sleeping. These definitions describe the APIs, not a guarantee that this environment exposes each one. [Linux clock_gettime documentation](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)

Time namespaces can change the origin of monotonic and boot-time readings. Therefore numeric resemblance between timestamps from two processes or runs does not itself establish a common epoch. Never compare cross-run monotonic values without explicit continuity evidence. [Linux time namespaces](https://man7.org/linux/man-pages/man7/time_namespaces.7.html)

### Proposed clock fields

Use integer nanoseconds internally for sample start, acquisition end, append begin and append completion. For browser-facing JSON, either encode potentially large nanosecond integers as decimal strings or explicitly convert to relative times before JavaScript Number arithmetic. Nanosecond units do not imply nanosecond accuracy.

Store at least:

- Fixed-grid origin, interval, deadline index and intended deadline
- Actual wake/sample-start time
- Signed deadline difference, plus a separately named nonnegative tardiness if wanted
- Collection duration; project-receipt collection duration if kept
- Encoding duration, append/sync/readback duration and whole-cycle duration
- Skipped-deadline count and overrun policy
- A monotonic bracket around each wall-time or optional alternate-clock acquisition
- Observer CPU consumed during collection and during the full cycle

An append cannot honestly contain its own fully completed fsync duration before that duration is known. Put the previous append's completed timing into the next record, or create a distinct bounded completion receipt. The last unreported duration is then explicitly missing. Avoid recursive “measure the measurement receipt” designs.

The fixed-grid scheduler should advance to the first future deadline after an overrun while recording the skipped indices. It should not issue a burst of backfilled fake observations. Deadline-index calculation needs tests around exact boundaries, floating-point or integer rounding, a long overrun, and clock invalidity. Root has independently selected this as a first implementation priority.

### A bracket is an uncertainty interval

For a wall-clock read W performed between monotonic reads M1 and M2, a practical estimate of wall-minus-monotonic offset is W minus the midpoint of M1 and M2, with acquisition uncertainty at least half the bracket width. This is an interval estimate, not calibration against an external time standard. Make separate brackets for RAW and BOOTTIME if they are available.

Interpret differences conservatively:

- A wall-minus-monotonic step larger than bracket uncertainty is evidence of changed clock relationship, not proof of a particular synchronization mechanism
- An increase in boot-minus-monotonic is consistent with suspend accounting under the documented clock semantics; it does not identify a provider event
- A raw-versus-monotonic slope may be consistent with frequency correction, but short windows and acquisition error can dominate it
- An increase in elapsed time without much process CPU could be sleeping, blocking, scheduling delay, suspension, or simply time outside the measured operation

Python documents clock information and warns that sleep can last longer than requested because of scheduling. Record the actual implementation metadata once per run and treat resolution as a property distinct from accuracy. [Python 3.12 time](https://docs.python.org/3.12/library/time.html)

## 4. A deliberately selective metric portfolio

### A. First-class observability metrics

These have greater immediate value than additional hardware gauges:

- **Observation age:** time since the last verified record, with the clock-domain qualification attached
- **Deadline coverage:** observed deadline indices versus planned eligible indices; distinguish late observations, deliberately skipped deadlines, and unobserved periods
- **Blind-interval inventory:** boundaries of known gaps, last-good evidence and first later evidence, without a fabricated cause
- **Acquisition width:** duration of each multi-source sample, since a wide sample is not simultaneous
- **Observer tax:** own CPU time, acquisition elapsed time, persistence elapsed time, bytes emitted and read, and descriptor high-water count
- **Metric availability trajectory:** first observed, latest observed, and reason transitions for every optional source
- **Integrity frontier:** last fully validated record, last sealed segment, last verified publication, and any unvalidated open tail
- **Configuration drift:** controlled changes in collector/schema/interval/options that require new comparison strata

These are proposed analytic quantities. Their usefulness is a design judgment, not a claim made by a kernel manual.

### B. Observer-process metrics

Read only the observing process's own permitted interfaces. Useful optional additions include current RSS estimate, maximum RSS, minor/major page faults, voluntary/involuntary context switches, and self scheduler wait/run counters. Linux `ru_maxrss` is a high-water mark in KiB, not current resident memory; getrusage's fault and switch counters can describe changes without identifying their cause. [getrusage](https://man7.org/linux/man-pages/man2/getrusage.2.html)

`/proc/self/status` offers compact self status fields, but current-memory figures have accounting qualifications. Keep “estimate” in the label rather than implying precision. [proc_pid_status](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)

If available and semantically verified, self `schedstat` gives running time, runqueue waiting time and timeslices. This could help distinguish scheduler waiting from broader elapsed delay, but a zero without validated accounting is not proof that no wait occurred. Do not enable kernel accounting or inspect other tasks for this project. [Kernel scheduler statistics](https://docs.kernel.org/scheduler/sched-stats.html)

Self I/O counters can expose observer amplification. Read/write syscall bytes and storage-layer bytes are different quantities, and accounting may include waited-for children. A collector with no children has a simpler scope. Do not turn “bytes read” into a disk-bandwidth chart. [proc_pid_io](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html)

Read-only affinity size is a more relevant hint for scheduling a process than reported machine CPU count, but does not promise that many cores' worth of service. Read it without changing affinity. [sched_getaffinity](https://man7.org/linux/man-pages/man2/sched_getaffinity.2.html)

A read-only timer-slack value is useful context for a wake-up experiment, not an explanation of all jitter. No change to timer slack is proposed. [proc_pid_timerslack_ns](https://man7.org/linux/man-pages/man5/proc_pid_timerslack_ns.5.html)

### C. Cgroup metrics, conditional on a verified self mapping

Candidate names are `cpu.max`, `cpu.stat`, `memory.current`, `memory.max`, `memory.high`, `memory.events`, `memory.events.local`, and `pids.current`/`pids.max`. The documented hierarchy matters: memory.current includes descendants; ancestor restrictions can constrain a child; memory.high and memory.max are different controls; memory events may be hierarchical; cpu.max describes quota per period. These are local interface semantics, not dedicated-capacity promises. [Kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

For CPU consumption, prefer CPU seconds per elapsed second before inventing a percent denominator. Only display a quota-normalized ratio when the applicable finite quota and interval are established; label it as quota-normalized usage, not host CPU utilization. Do not assume that throttled-period count is a fraction of wall-clock seconds, or that throttled-time totals necessarily behave like one simple stopwatch. Version-specific interpretation of newer local throttling fields remains a research frontier, not a pilot dependency.

The resolver should inspect only allowlisted self metadata and the visible permitted cgroup mount. Mountinfo includes a mount root distinct from mount point, and cgroup namespaces can alter displayed path relationships. An implementation must reconcile them rather than assuming concatenation always works. If mapping cannot be proved safely, retain unknown. Never walk ancestors or use alternate paths to bypass an access denial. [proc_pid_mountinfo](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html), [cgroup namespaces](https://man7.org/linux/man-pages/man7/cgroup_namespaces.7.html)

### D. Pressure, not just consumption

If already exposed for the verified self cgroup, CPU, memory and I/O pressure can complement usage. PSI “some” concerns at least some stalled tasks; “full” concerns all non-idle tasks stalled together; cumulative totals support interval deltas. These are not interchangeable with resource use. System-level CPU full has special semantics and must not be read as a normal nonzero-capable utilization gauge. This proposal only reads pressure files; it does not register kernel triggers. [Kernel PSI documentation](https://docs.kernel.org/accounting/psi.html)

A pressure spike plus a missed deadline is more informative than a low average CPU value alone. It is still correlation, and scope must match before the two are compared.

### E. Filesystem metrics

Retain available bytes but add available inodes and explicit filesystem scope, if supported. `statvfs` distinguishes blocks available to an unprivileged process from total free blocks. Neither quantity by itself establishes a per-user quota or future successful allocation. [statvfs](https://man7.org/linux/man-pages/man3/statvfs.3.html)

For observer-owned artifacts, collect logical file bytes, optionally allocated blocks, complete-record count, sealed-byte count and readback hashes. Keep path aliases rather than public full paths. File length growth is attributable to this observer; free-space movement in a shared filesystem is not.

If a permitted metadata check establishes OverlayFS, inode/device observations need care: identity behavior depends on configuration and copy-up. The current logs do not establish that OverlayFS is in use. This is a conditional confound, not an environmental finding. [Kernel OverlayFS documentation](https://docs.kernel.org/filesystems/overlayfs.html)

### F. Resource limits and workflow events

Read-only self limits can identify configured descriptor, file-size, address-space or CPU ceilings where supported. They do not measure physical capacity or prove safe headroom. No limit changes or limit-exhaustion tests are proposed. [getrlimit](https://man7.org/linux/man-pages/man2/getrlimit.2.html)

Workflow metrics should distinguish dispatch, tool admission, process start, artifact creation, returned result, verification, publication request and publication readback. Count independently verified useful artifacts as a separate outcome. A reported receipt count is not a direct measure of agent cognition, productive effort, worker liveness or completeness.

## 5. Passive observation and active measurement

“Passive” means no intended synthetic workload. It does not mean zero influence. Reading counters consumes CPU; parsing creates allocations; checking files can alter caches; writing observations changes storage use; synchronizing them can delay the process.

Use three labeled modes:

1. **Baseline:** the established observer, with its version and cadence recorded
2. **Instrumented baseline:** the same work with bounded extra timing and self-accounting
3. **Active probe:** a clearly named experimental operation in an isolated observer-owned directory

Do not pool these modes into one performance series without labels. Do not run several probes concurrently. A public chart should allow the reader to hide active-probe intervals and should still display that they occurred.

### Shared pilot envelope

These are proposed limits, not measurements or authorization to run them:

- Select at most three probes for an initial pilot; do not execute the whole catalog automatically
- One probe at a time, one owned process by default, no subprocess unless explicitly part of the selected protocol
- No network traffic, package installation, credential access, environment dumps, other-process inspection, kernel tracing, namespace changes, cache dropping or resource-limit changes
- New regular files only in a fresh experiment directory; preserve uploaded originals, canonical artifacts and existing logs
- Aggregate pilot cap: 10 CPU seconds, 8 MiB application data read, 2 MiB new application data written, 64 owned files, 16 simultaneously open descriptors, and 60 minutes of elapsed observation
- A per-probe cap always overrides a larger aggregate cap
- Record actual counters and budget use; skip the next operation when the next known cost would exceed a cap
- Stop a probe on permission denial, malformed source, identity discontinuity, unexpected path/type, integrity mismatch, user cancellation or a budget exceedance; do not switch routes around a denial
- Review rather than automatically repeat failed or inconclusive probes

Elapsed-time caps are **cooperative stopping targets**, not guarantees that a filesystem syscall cannot block beyond them. A deadline checked before and after fsync does not bound a stuck fsync. If a blocking call exceeds budget, record the overrun on return, perform no further experimental operations and report the limitation. No watchdog or kill machinery is hidden in this proposal.

## 6. Bounded experiment catalog

Every study below is **unexecuted**. The outcome clauses are decision rules, not predicted results.

### E1. Clock brackets and domain disagreement

**Question:** Does apparent wall/monotonic disagreement exceed the uncertainty of taking separate readings?

**Protocol:** In one process, take 32 small triplets of monotonic-before, chosen clock, monotonic-after, separated by ordinary short sleeps. Measure REALTIME; measure RAW and BOOTTIME only when directly supported. Retain every bracket, including unusually wide ones. Repeat the same set once at an existing later checkpoint, without adding a long-lived background process.

**Budget:** At most 128 bracketed acquisitions per invocation, 10 seconds elapsed, 0.25 CPU seconds, 64 KiB output, no experiment data file other than the result.

**Control:** Alternate acquisition order across groups; include monotonic-to-monotonic brackets to estimate call/path overhead. Keep warm-up samples labeled instead of silently discarding them.

**Stop:** Unsupported optional clocks are individually marked unavailable; any negative monotonic bracket or identity discontinuity stops comparison. No clock setting or external time service is used.

**Confounds:** Scheduling between calls, Python call overhead, frequency adjustments, namespace offsets and virtual clock behavior. A 1 ns nominal resolution does not validate physical nanosecond timing.

**Action:** If most apparent discrepancy fits within acquisition brackets, show an uncertainty band and avoid a “clock instability” alarm. If a large residual remains, preserve a clock-domain event and suspend cross-domain rate calculations until reviewed.

### E2. Collector tomography through bracketing

**Question:** Which part of an observation consumes elapsed time?

**Protocol:** Bracket own-resource reads, OS-view reads, receipt reads, encoding and persistence separately. For persistence completion, report in the next record. Compare like-for-like cycles with a versioned collector. Do not change source order during the initial comparison.

**Budget:** Add timing around 12 already-planned samples; at most 32 extra clock reads per sample, 0.5 extra CPU seconds total and 128 KiB added log data. Duration is bounded by those existing sample opportunities, not a new permanent monitor.

**Control:** Same baseline cadence and same enabled sources. Classify segment-rotation cycles separately from ordinary appends.

**Stop:** Extra CPU or record-size budget exceeded; a source newly denied; any sample needing more than its configured maximum collection duration is marked slow and the extension is paused after that sample.

**Confounds:** Bracketing adds work; first access differs from warm access; serialization depends on record size; rotation changes the write path.

**Action:** If receipt reads dominate, separate their cadence from resource sampling. If persistence dominates, make checkpoint policy an explicit reliability/latency choice. If wake-up delay dominates, adding more collectors is unlikely to explain it.

### E3. Counterbalanced measurement-tax comparison

**Question:** How much does full durable observation perturb the very behavior being described?

**Protocol:** Compare A, a minimal time/self-counter read, with B, full allowed collection plus a small private append, fsync and readback. Use eight paired blocks with predeclared AB/BA ordering, one block per ordinary checkpoint. All outputs go to disposable probe files, never the live log. Pair within a short window and retain order labels.

**Budget:** Eight pairs, at most 16 tiny appends, 64 KiB written and 128 KiB read, 2 CPU seconds, 10 minutes elapsed. At most two result/data files open.

**Control:** Same source set, fixed record sizes where feasible, no unrelated synthetic workload. Record initial and later pairs rather than calling the first one “bad.”

**Stop:** One operation over 1 second triggers no further pairs; any error or cap breach ends the study. This threshold is a conservative project choice, not a claim that 1 second is a system limit.

**Confounds:** Shared storage activity, caches, writeback batching, unavoidable order effects and counter-read perturbation. Eight pairs estimate local effect size; they do not support universal tail probabilities.

**Action:** If B has little CPU but large elapsed cost, present persistence time separately. If B's cost approaches the sampling interval, lower frequency or change the reviewed checkpoint strategy before increasing telemetry.

### E4. Sparse phase diversity instead of a blind fixed phase

**Question:** Does a once-per-minute observer miss short or phase-locked disturbances?

**Protocol:** Preserve the main cadence. In a separate selected window take 24 minimal clock/self-counter observations at a predetermined, reproducibly shuffled set of offsets within six minutes. Do not wake in a tight loop. Compare the sparse phase-diverse samples with the ordinary fixed-grid samples as two distinct designs.

**Budget:** 24 added observations, six minutes elapsed, 0.5 CPU seconds, 64 KiB output; no extra fsync per micro-observation, one bounded result write at the end.

**Control:** Publish the chosen offsets and phase coverage. Record actual acquisition times, not just planned offsets. Keep contemporaneous baseline observations labeled.

**Stop:** Any acquisition exceeds 100 ms or the CPU cap; do not increase the rate to investigate a disturbance during the same study.

**Confounds:** Added wake-ups disturb the process; naturally varying workload can coincide with phase. Failure to find phase dependence is not proof that short disturbances never occur.

**Action:** If additional samples reveal events absent from baseline, describe baseline as low-frequency trend observation. Decide whether short scheduled diagnostic windows are worth their cost; do not silently advertise the baseline as a latency monitor.

### E5. Scope-mapping qualification

**Question:** Can the observer prove which permitted self resource scope its counters describe?

**Protocol:** Read only allowlisted self cgroup membership and mount metadata, parse bounded content, and produce a sanitized mapping certificate or typed reason for failure. Validate the proposed mapping using the visible allowed mount only. No directory-tree enumeration, ancestor search or alternative namespace access.

**Budget:** One invocation; at most four metadata reads and eight already-approved candidate scalar/interface reads, 256 KiB total input, 32 KiB output, 0.5 CPU seconds, five seconds elapsed.

**Control:** Offline parser fixtures for root-relative mounts, escaped mount fields, missing controllers, malformed input and ambiguous mapping. These fixtures do not require any privileged environment manipulation.

**Stop:** Ambiguity or denial means unknown. A rejected `..` path is not traversed. No attempt is made to remount or enter another namespace.

**Confounds:** Different kernel/filesystem exposure, namespace views, mount configuration and source mutation during acquisition.

**Action:** Success enables carefully scoped metrics. Failure is itself a useful result: keep OS-exposed views qualified and refrain from drawing container-allocation conclusions.

### E6. Counter-interval consistency and read skew

**Question:** Are derived rates more precise than the source acquisition permits?

**Protocol:** At six ordinary checkpoints, bracket a selected accessible cumulative counter with two readings around the rest of the selected acquisition. Preserve the enclosing interval and calculate a range rather than pretending each source was simultaneous. If the counter decreases, begin a new scope epoch instead of taking an absolute value or clipping to zero.

**Budget:** Twelve additional counter reads, 64 KiB input, 16 KiB output, 0.25 CPU seconds, six existing checkpoint opportunities.

**Control:** Use the same counter identity and a verified monotonic domain. Compare an ordinary single-read estimate with the bracket-derived interval.

**Stop:** Missing source, identity change, counter reset or budget breach stops interval aggregation.

**Confounds:** Counter batching, unrelated activity inside the same cgroup and events between reads. This does not measure an atomic system snapshot.

**Action:** If skew is substantial relative to the claimed rate changes, widen error bounds or slow the interpretation rather than smoothing away the uncertainty.

### E7. Open descriptor versus atomic pathname replacement

**Question:** Can an analyzer distinguish a stable open object from a newly replaced pathname?

**Protocol:** In a new probe directory create two small versioned files. Open a reader on version A; replace the visible pathname with a fully written version B using same-directory atomic rename; compare the already-open reader with a freshly opened reader. Repeat eight times, recording version markers and hashes. This can be performed serially in one process; it need not spawn a reader process.

**Budget:** Eight replacements, 4 KiB payload per version, at most 64 KiB written and 128 KiB read, four owned filenames, four open descriptors, 0.5 CPU seconds, 10 seconds elapsed.

**Control:** A no-replacement read of the same file and a hash comparison against both known complete versions. Never overwrite existing project files.

**Stop:** Any result other than the protocol's recognized complete states, any filesystem error or any cap exceedance; preserve the tiny evidence rather than retrying blindly.

**Confounds:** This tests ordinary visible semantics, not power-loss recovery. Cross-filesystem rename is excluded. Overlay configuration, if actually present, can affect identity observations.

**Action:** Design the analyzer to acquire a stable finite object or detect source replacement; never treat an mtime-only check as a proof of snapshot identity. Linux documents atomic replacement and the continued validity of open descriptors across rename. [rename](https://man7.org/linux/man-pages/man2/rename.2.html)

### E8. File sync, directory sync and later survival ladder

**Question:** Which layer of persistence evidence do we actually have?

**Protocol:** Create one 4 KiB marker with a random nonsecret run token and hash; flush and fsync its contents; rename within the fresh directory; request directory fsync where supported; record each completion separately. Read it at the next already-authorized checkpoint and after a naturally occurring future session/environment boundary if that boundary occurs within the task's observation period. Do not induce a restart, crash or eviction.

**Budget:** One marker and one small receipt, at most 16 KiB written and 64 KiB read, 0.25 CPU seconds per acquisition. Initial operation target five seconds; at most four later reads at existing checkpoints. Boundary waiting has no extra resident process.

**Control:** Known pre-write content hash and explicit identity of the marker. Verify an artifact through independent authorized publication readback only if that publication is already part of the project workflow.

**Stop:** Unsupported directory fsync is recorded, not worked around. The study ends at the selected observation window or after the relevant boundary is observed; if no boundary occurs, survival across that boundary remains untested.

**Confounds:** File sync success is an interface acknowledgment; same-session readback can hit caches; storage and environment retention policies are outside this local test. A successful later read is evidence of survival across that particular boundary, not immortality.

**Action:** Use an evidence ladder: bytes written; same-session readback; file sync acknowledged; directory sync acknowledged; later same-environment readback; observed boundary survived; independently published checkpoint verified. Linux explicitly distinguishes file fsync from syncing the containing directory. [fsync](https://man7.org/linux/man-pages/man2/fsync.2.html)

### E9. Natural process/session survival cohort

**Question:** Does loss of the tool's managed-session handle coincide with cessation of artifact production?

**Protocol:** Use only the already-authorized observer run and its supported session-status interface. At existing checkpoints record status outcome, latest validated record and terminal-state evidence. Do not create detached fallback processes, ignore platform lifecycle limits, reopen denied interfaces or trigger environment replacement.

**Budget:** No new long-lived process; at most one status read and one bounded log-prefix read per existing checkpoint, up to a selected 60-minute study window. Limit total log input to 2 MiB by incremental verified reads; output at most 64 KiB.

**Control:** Distinguish session-handle status, process self-recording, artifact visibility and publication availability. They are separate observations, not a single health bit.

**Stop:** User cancellation, run terminal state, requested window end or access loss requiring user input. Do not repeatedly relaunch an unknown outcome.

**Confounds:** The observer and its artifact store can share a failure domain. A missing handle may be orchestration bookkeeping. A surviving file may be stale. A missing stop record gives neither death time nor cause.

**Action:** Treat the last positive sample as a last-known-good bound. If a later read proves no new artifact, report an observation gap; do not rename it a container crash. Use explicit new run IDs after authorized restarts.

### E10. Timestamp granularity and metadata honesty

**Question:** Can file timestamps distinguish writes at the cadence the analyzer assumes?

**Protocol:** On one disposable file perform eight tiny, spaced updates and read content, size and timestamp metadata after each. Keep known sequence numbers inside the file. Compare content changes with timestamp changes; do not use timestamps as the integrity oracle.

**Budget:** Eight writes of at most 128 bytes, 16 metadata reads, one file, 16 KiB total I/O, 0.25 CPU seconds, five seconds elapsed.

**Control:** Re-read without writing once, and compare sequence/hash with timestamp deltas. Keep actual operation brackets.

**Stop:** Metadata inconsistency, unexpected file type, access denial or cap exceedance.

**Confounds:** Timestamp resolution, caching and acquisition ordering. Even one stat call can report fields associated with different instants under concurrent mutation; the test is deliberately single-writer. [stat](https://man7.org/linux/man-pages/man2/stat.2.html)

**Action:** If consecutive versions share timestamps, stop using mtime as a freshness proof. Use content version, byte prefix and hash frontier instead.

### E11. Offline integrity classification challenge

**Question:** Does the analyzer reject corrupted, ambiguous and incomplete evidence without discarding valid prefixes or claiming authentication?

**Protocol:** Construct tiny synthetic fixtures, not modified real logs: one missing middle record, reordered records, duplicated sequence, different run ID, truncated final line, altered final open record, mismatched sealed hash, manifest omission, duplicate open/sealed names, unknown metric, negative counter delta and changed clock epoch. Classify each using the proposed evidence contract.

**Budget:** At most 24 fixtures, 256 KiB total, 24 owned files, one CPU second, 10 seconds elapsed.

**Control:** A complete valid fixture and an explicitly in-progress open-tail fixture. Expected results are declared before implementation.

**Stop:** Any fixture exceeding its bound; preserve failures and stop before replacing any canonical analyzer or actual evidence.

**Confounds:** Synthetic testing cannot establish survival through real failures. It tests classification logic and reader assumptions, which is exactly its intended outcome.

**Action:** Make the difference among invalid evidence, valid closed evidence and a valid prefix with unresolved tail visible. A locally recomputable hash chain is integrity evidence relative to a retained checkpoint, not proof that its writer told the truth.

### E12. Work outcome versus resource correlation

**Question:** Do environment signals help make a concrete workflow decision?

**Protocol:** Select one already-requested ordinary task class with clear start, artifact and verification receipts. Compare a small number of naturally occurring instances. Attach contemporaneous observation coverage and environment mode; avoid launching redundant jobs merely to grow a sample size.

**Budget:** Retrospective analysis of up to ten instances, 1 MiB of allowlisted minimized receipt data, one CPU second, no task launches and no network probes. Output up to 128 KiB.

**Control:** Stratify by artifact size/task variant, source version, instrumented mode, cache/warm-start status if known, and verified coverage. Keep failed and censored instances.

**Stop:** Essential outcome evidence unavailable, privacy review fails, or incomparable task definitions. Report why comparison is invalid rather than manufacturing a score.

**Confounds:** Task complexity, service latency outside the container, model variability, user interaction, shared I/O and selection bias. These may dominate the resource gauges.

**Action:** A useful conclusion might be “checkpoint before this external step” or “the present data cannot explain these delays.” Neither requires a causal claim from a correlation plot.

## 7. Survival, censoring and identity

Maintain separate identities for experiment, observer process incarnation, run, clock epoch, resource scope, artifact version and external publication. PID alone is not a durable identity. A startup token created by the observer is useful for its own records; if self process start time is consulted, its clock-tick units must be retained. Do not enumerate other processes to discover identities. [proc_pid_stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)

Distinguish these terminal descriptions:

- Completed with a verified stop record
- Explicitly stopped with a verified reason
- Failed with a verified local error
- No later records found during a specified check window
- Status interface unavailable
- Current state unknown

The older run fits missing-terminal/last-known-good evidence; a precise crash time is unsupported. Runs still producing records are right-censored for eventual-lifetime analysis. Runs deliberately ended by duration are administratively censored for a different question. Do not estimate a platform failure rate by counting every missing stop as a crash.

A canary file does not witness the process between reads. A process does not independently witness storage that fails with it. Two records from the same process are not two independent observers. These are judgments about evidence independence, not missing telemetry that can be cured by adding another local gauge.

## 8. Artifact integrity and trustworthy publication

Preserve original bytes. Prefer closed-segment publication. A live reader should either obtain a finite snapshot and say exactly which prefix it validated, or retry only under a declared bounded concurrent-write policy. It must not silently accept a torn final line as a complete record, and it should not describe a briefly incomplete live tail as permanent corruption without a stable recheck.

Validate schema, run ID, sequence, record size, newline framing, hash links, manifest membership, segment order and sealed byte hashes. Keep the independently retained terminal hash of a publication. A chain whose entire contents and final digest live in the same writable place can be rewritten consistently; hash chaining alone is not authentication.

Publication should bind:

- Exact source and collector versions
- Exact closed artifacts and their byte hashes
- Coverage interval and explicit gaps
- Sampling and experimental modes
- Sanitized metric definitions and missingness summary
- Review status and the source of every claim
- Exact remote commit plus readback verification of the expected bytes

Retain the difference between an upload request, acknowledged remote commit and verified remote readback. A saved receipt about publication is useful provenance, but it is not the same operation as newly verifying the remote at chart-render time.

Do not publish raw mount tables, cgroup paths, environment variables, command lines, machine-wide process lists, authentication material, user content or host identities merely because they can be read. Export only necessary allowlisted summaries. Hashing a sensitive or low-entropy identifier is not automatically anonymization.

## 9. Bad metrics and misleading charts

1. **“Nine CPUs available” from os.cpu_count.** This confuses reported topology with affinity, quota, contention and service. Label the reported view and leave effective capacity unknown.
2. **“10.45 GB container RAM” from MemTotal.** The inspected logs do not establish this scope. OS memory views and container constraints belong in separate panels.
3. **“CPU percent” without a denominator.** Process CPU seconds per wall second, cgroup quota-normalized usage and host CPU use are different measurements.
4. **“Observer memory usage” from max RSS.** A high-water mark cannot fall. A flat trace can coexist with changing current RSS.
5. **“Everything changed” from resource_changed.** Cumulative self CPU makes change nearly inevitable. Separate configuration change, resource-level change, source-availability change and receipt change.
6. **“Uptime 100%” from present rows only.** It drops the periods when the observer failed to report. Display planned coverage, observed opportunities and blind intervals.
7. **A continuous line across run boundaries.** It fabricates continuity. Break lines at clock/scope/run changes and shade unobserved periods.
8. **A smooth one-minute curve used as a tail-latency claim.** Sparse surviving samples cannot see every short stall. Use points and measured interval widths.
9. **p99 from 15 or 19 samples.** Depending on the estimator, it is approximately the sample maximum with very little tail information. Show n, ordered observations, median/range and a declared estimator; reserve reliability claims for an adequate design.
10. **Averaging interval rates without considering interval widths.** A ten-second interval and a ten-minute interval should not have equal weight when estimating total CPU per total elapsed time. Preserve sums and coverage.
11. **Interpolating missing metrics as zero.** Unknown cgroup readings do not mean zero memory, zero pressure or no quota.
12. **Filesystem free-space decrease attributed to Lumen.** Shared filesystem movement is not observer-owned byte growth. Show both, with different scopes.
13. **Throttled periods plotted as percent of seconds.** Counts and elapsed duration are different dimensions. Use explicitly defined ratios or raw deltas.
14. **Load average labeled CPU utilization.** Linux load averages concern runnable and uninterruptible tasks over defined windows. They are not a percentage of processor time. [proc_loadavg](https://man7.org/linux/man-pages/man5/proc_loadavg.5.html)
15. **A dual-axis correlation chart implying cause.** Arbitrary scales can make unrelated series appear synchronized. Prefer aligned small panels, explicit lag assumptions and uncertainty.
16. **A cumulative receipt count labeled productivity.** It rewards tiny or duplicated events and ignores correctness, usefulness and missing outcomes.
17. **Log-scale axes without disclosure.** They can make a serious small absolute threshold crossing appear visually minor. Use task-relevant thresholds with units.
18. **False precision in a polished display.** Six decimal places do not compensate for unknown scope, censored samples or asynchronous acquisition.

A good first display would have an evidence-status header, a run/deadline coverage strip, separate observer and OS-view panels, a cost panel, and an integrity/publication frontier. Every chart should include source, unit, sample count, time coverage and gap policy.

## 10. Statistical discipline

Predeclare the question, metric and decision before each probe. Retain negative and inconclusive results. Use effect sizes in understandable units before statistical significance. Small pilot studies are for qualifying instrumentation and detecting large practical effects, not ranking cloud platforms.

Never treat adjacent minute samples as independent merely because they are separate rows. Shared state, smoothing windows, caches and workload bursts create dependence. Confidence formulas that assume independent trials should not be pasted onto an autocorrelated timeline. Repeated looks and trying many metrics also increase the chance of impressive-looking coincidences.

Separate warm-up, normal append and segment-rotation regimes. Stratify by collector revision. Record measurement availability alongside values. Define exclusion criteria before inspection and preserve excluded samples with reasons. A performance regression comparison is invalid if one version observes more sources, writes larger records or uses a different synchronization policy without that change being accounted for.

Where uncertainty overwhelms the proposed effect, the right result is “not resolved at this observation granularity.” Increasing chart smoothness is not a scientific response.

## 11. Priority order and gates

### Priority 0: make existing evidence honest

Implement fixed-grid deadline bookkeeping, distinct timestamp locations, typed missingness, safe snapshot classification, explicit run gaps and publication-safe source labels. Correct the records-versus-samples terminology. Avoid relying on resource_changed as an environmental signal.

**Gate:** Synthetic cases classify correctly and the existing logs render without invented cgroup values, continuity or terminal causes.

### Priority 1: learn the observer's cost

Select E1 and E2 first. Select E3 only if the initial bracketing leaves meaningful uncertainty about cost. Leave the live baseline unchanged until a reviewed collector revision is ready.

**Gate:** Added cost fits budget, active intervals are tagged, and timing metadata has a nonrecursive completion design.

### Priority 2: qualify scope and storage semantics

Choose E5 plus the small file experiments E7/E8 as independently reviewed candidates, not as an automatic combined run. If scope remains unavailable, publish that limitation and proceed with useful self/workflow evidence.

**Gate:** No traversal around denials, no host identity leakage, and persistence labels match the actual evidence ladder.

### Priority 3: answer a concrete work question

Use E9 and E12 for a bounded observation window or an already-open task. Add E4 only if low-frequency aliasing is relevant to the question. E6 helps when rate uncertainty matters. E10/E11 strengthen analyzer correctness before broad comparisons.

**Gate:** There is a decision that the result could change, an authorized task/outcome, a defined end of observation and enough comparable evidence to support the intended claim.

### Explicitly defer

No CPU saturation, memory allocation to a limit, disk-fill tests, fork/descriptor exhaustion, induced OOM, crash/reboot experiments, global cache manipulation, network throughput or reachability scanning, privilege/capability exploration, tracing of other processes, watchdog evasion, or attempts to keep a process alive outside supported lifecycle controls. These are unnecessary for the proposed first measurement program.

## 12. Judgments that metrics cannot make for us

**Importance.** A one-second delay may be irrelevant during overnight analysis and decisive during an interactive exchange. The observer cannot derive that value judgment from CPU counters.

**Correctness.** A produced file can be fast, hash-consistent and wrong. Domain-specific verification must remain an independent outcome.

**Consent and privacy.** A useful metric may still expose details that should not be published. The choice of source and granularity needs review, not merely redaction after broad collection.

**Attribution.** The container may display a symptom whose cause lies in orchestration, remote services, work complexity or the observer itself. Absence of a local explanation is not evidence of provider misconduct.

**Tradeoffs.** Frequent fsync may improve local recovery evidence while consuming latency and I/O. The right checkpoint interval depends on the cost of losing work and the actual retention model, not a universal performance maxim.

**Meaningful work.** Low CPU during a wait is not inactivity in the human sense; high CPU is not usefulness. Completion, verified artifacts, resolved uncertainties and the user's intended outcome are the appropriate context.

**Evidence sufficiency.** We must decide when uncertainty is acceptable for a reversible choice, when another observation is worthwhile, and when further local measurements cannot answer the question. More metrics are not automatically more knowledge.

**Fair reporting.** The project should publish failed probes and limitations alongside successes. A lack of dramatic results can be valuable: it may establish that a simpler observer is sufficient.

## 13. Verification frontier and unfinished checks

### Completed for this contribution

- Read the specified observer, tests and plan; read managed-launch/restart metadata
- Inspected and independently checked hash/sequence consistency of finite snapshots from both managed runs
- Identified concrete schema, scheduling, scope and persistence interpretation issues in the inspected code
- Consulted primary Linux kernel/man-page and Python documentation linked beside the relevant claims
- Designed the bounded studies above without executing them

### Not completed or not established

- No new runtime capability inventory, cgroup-mount qualification or pressure availability check was executed
- No proposed probe, benchmark, mutation fixture or process-lifecycle experiment was run
- Existing unit tests were read, not rerun as part of this contribution; root's later verified test results are separate evidence
- No current observer liveness claim is made from the earlier 20:13 snapshot
- No provider storage-retention guarantee, physical time accuracy or root-cause attribution was established
- Newer cgroup throttling-field semantics, precise kernel configuration, current-memory accounting limitations and any OverlayFS behavior need version/environment-specific qualification before depending on them
- Probe CPU and elapsed budgets are conservative design targets; their attainability and measurement overhead are unverified until a selected pilot is reviewed and run
- The proposal has not been checked against root's latest collector changes. The initial static findings may already be addressed

The strongest usable result is already clear: make coverage, uncertainty, observer cost and evidence integrity visible first. Then add the smallest measurement that could change a real decision.
