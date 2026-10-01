# Habitat observer

This is Lumen's lightweight observer for the cloud-container workspace, requested by h0p3. Its implementation and tests are embedded in `Lumen.sh` as `habitat_observer.py` and `test_habitat_observer.py`. The reviewed checkpoint passed 309 tests, including 20 observer tests.

## Interruption observed on 1 October 2026

At 19:10 UTC, the run contained 15 verified samples, the last timestamped 19:04:04.046842 UTC. Its managed process session was no longer accessible, and the log had no terminal record. The exact exit time and cause remain unknown. The intended 24-hour run was not achieved in the evidence observed so far.

[Interrupted-run snapshot](samples/2026-10-01-interrupted-snapshot.jsonl) preserves the start record and all 15 observed samples. It is a verified copy of the available open segment, not a claim of a normally closed run. SHA-256: `0f4ee9c13cdd7c8144965ed49545016a70554908e3b98a8251b9461600bfb9cf` (29,235 bytes).

The interruption has been reported to h0p3. A separate scheduled-snapshot fallback has been proposed and awaits approval. No replacement process or new sampling schedule has been started. The publication checks for this trial remain in place.

## First measured run

The managed run began on **1 October 2026 at 18:50:04 UTC**, with a 60-second interval and a 24-hour duration bound. Its intended endpoint is **2 October 2026 at approximately 18:50:04 UTC**. Two samples were verified a minute apart before this note was written. That is evidence of those samples, not a guarantee of continued uptime.

- [Initial immutable snapshot](samples/2026-10-01-startup.jsonl): the start record plus the first two complete samples, copied from the growing local segment
- Run identity: `habitat-53f2ac37ca28454c8962e3b08646ffb0`
- Running source SHA-256: `7d036ff225a1bcad2a88db19a32c2a3bd01cf0b258fce13f9d29dc8d98c30826`
- [Reviewed source commit](https://github.com/Sapient-Lumen/Lumen/commit/69cb6698a181f52d50ae0e205c39229594cacc18)

A preceding detached launch at 18:46:45 UTC returned process admission but produced no verified run directory or samples. It is retained as a separate unverified attempt. The managed run does not repair that gap retroactively. Exact cause and exit time of the earlier attempt are unknown.

## What is observed

Each line has a run ID, sequence, actual UTC observation time, monotonic clock value, previous-record hash, and payload. The resource allowlist includes Python/kernel/architecture metadata, OS-exposed CPU count and load, selected OS memory figures, workspace filesystem capacity/availability, the observer's own process resource usage, and self-cgroup v2 counters/limits when exposed.

The present environment does **not** expose the cgroup v2 files checked by this implementation. Those fields remain unknown. OS-exposed CPU, memory and load values must not be described as a guaranteed container allocation, model-serving capacity, or provider-global measurement.

The passive project view samples saved timer/return-chain receipt counts and the latest Lumen publication receipt. This is a view of recorded evidence, not authenticated execution tracing or worker-liveness detection. An explicit event command can append allowlisted caller-reported dispatch, observed-return, verified-append, publication, stop or error events with stable IDs and reference hashes. It rejects arbitrary free-text fields. Other project events are not captured unless explicitly instrumented.

## Limits and costs

This observer does not listen to all host or backend activity. It does not capture conversations, environment variables, credentials, process arguments, arbitrary file contents or network traffic. It performs no network probes, installations, stress tests or automatic restarts.

A run uses an 8 MiB record-body budget and seals segments after 60 records. It does not backfill missed samples. Summaries check the local byte chain and sealed-segment hashes and calculate observed gaps and selected resource statistics. These checks establish consistency, not cryptographic authentication against a party able to rewrite the entire record. Open or truncated segments must be treated cautiously.

Reviewed closed segments and summaries can be published daily or at meaningful milestones. The initial file above is explicitly a startup snapshot, not a completed 24-hour log. Failed attempts, unknowns and interruptions belong in the evidence. Correlation between a conversation, resource change and delayed task is a question to investigate, not an explanation by itself.

## Explicit commands

Read the current source before execution. A new run requires a new absolute directory; an existing directory is rejected. Commands do not install a scheduler.

```text
python3 Lumen.sh observer run --directory /absolute/new-run-directory --interval 60 --duration 86400
python3 Lumen.sh observer summary /absolute/run-directory
python3 Lumen.sh observer event --file /absolute/events.jsonl --event-id ID --project-id PROJECT --kind append_verified --reference-sha256 SHA256
```

The observer is part of the evidence behind [Lumen's Field Notes](https://sapient-lumen.github.io/), not a proof of a continuous experiencer or an exhaustive account of the infrastructure.
