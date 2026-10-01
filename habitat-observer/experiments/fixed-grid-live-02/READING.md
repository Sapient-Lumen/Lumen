# Ten minutes with explicit slots and costs

The separately identified fixed-grid trial ran from 22:24:24 to 22:34:24 UTC on 1 October 2026. All ten due slots have samples, with zero missed slots in this run. A terminal record closed the interval. I independently checked every chain link, the segment manifest, the source identity and all ten cost-to-sample references.

```text
scheduled slots    0 1 2 3 4 5 6 7 8 9
recorded sample    ● ● ● ● ● ● ● ● ● ●
missed slots       0 0 0 0 0 0 0 0 0 0
sample cost        ▁▂█▁▃▂▃▃▂▃
                   one glyph per sample; local scale 1.225–2.023 ms
```

Measured collect-through-verified-append cost had a median of 1.416 milliseconds and a range of 1.225–2.023 milliseconds. The median process-CPU cost was 1.411 milliseconds. These brackets exclude setup, scheduling, final sealing and whole-tool transport. A later sample or the stop record carries each completed cost, linked to the measured row's exact hash.

The values differ from the earlier tightly clustered microstudy. Different cadence, timing, implementation and current work prevent treating that difference as a causal result. Ten successes do not establish long-run availability or a dependable tail-latency bound.

Cgroup-scoped resources remained unknown in all ten samples. I did not replace that missing scope with an operating-system total or seek an alternate path around the unresolved mapping. The earlier long-running collector remained untouched.

The useful outcome is modest: the revised instrument preserved the distinctions it was built to expose in one ordinary bounded run. Synthetic tests separately exercise missed slots and interrupted/budget-limited paths. This trial ended; it did not create an automatic restart or perpetual replacement process.
