"""The Observer of The Habitat: offline, bounded, Unicode evidence atlas.

Reads a single immutable JSONL snapshot. No probing, publishing or live mutation.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
BARS = '▁▂▃▄▅▆▇█'


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def utc(s):
    v = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    if v.tzinfo is None:
        raise ValueError('timezone required')
    return v.astimezone(dt.timezone.utc)


def load_snapshot(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('snapshot exceeds 8 MiB budget')
    if not raw or not raw.endswith(b'\n'):
        raise ValueError('empty or truncated snapshot')
    previous = '0' * 64
    rows = []
    run = None
    for line in raw.splitlines(keepends=True):
        r = json.loads(line)
        if r.get('schema') != 1 or r.get('sequence') != len(rows) + 1:
            raise ValueError('schema or sequence mismatch')
        if r.get('previous_sha256') != previous:
            raise ValueError('hash chain mismatch')
        if not isinstance(r.get('run_id'), str):
            raise ValueError('run identity missing')
        if run is not None and r['run_id'] != run:
            raise ValueError('mixed run identities')
        if not number(r.get('monotonic_ns')):
            raise ValueError('invalid monotonic observation')
        if rows and r['monotonic_ns'] <= rows[-1]['monotonic_ns']:
            raise ValueError('non-increasing monotonic observations')
        utc(r['observed_utc'])
        if not isinstance(r.get('payload'), dict):
            raise ValueError('payload missing')
        run = r['run_id']
        previous = hashlib.sha256(line).hexdigest()
        rows.append(r)
    if rows[0]['payload'].get('kind') != 'start':
        raise ValueError('snapshot must include run start')
    return rows, hashlib.sha256(raw).hexdigest(), len(raw)


def describe(values):
    a = sorted(v for v in values if number(v))
    if not a:
        return {'n': 0}
    # Nearest-rank empirical quantiles; no distributional confidence claim.
    def q(p):
        return a[max(0, math.ceil(len(a) * p) - 1)]
    return {'n': len(a), 'min': a[0], 'median': q(.5), 'p95': q(.95),
            'max': a[-1], 'mean': math.fsum(a) / len(a)}


def observed(resource, *keys):
    try:
        v = resource
        for k in keys:
            v = v[k]
        return v if number(v) else None
    except (KeyError, TypeError):
        return None


def value(resource, key, *keys):
    obj = resource.get(key, {})
    if obj.get('status') != 'observed':
        return None
    return observed(obj, 'value', *keys)


def timeline(samples, interval, key, width=60):
    """Last width nominal time bins, with empty bins kept explicitly empty.

    Samples are assigned by monotonic observation time from the first sample.
    Multiple samples in one bin are averaged and counted, never silently selected.
    """
    if not samples:
        return {'glyphs': '', 'missing_bins': 0, 'collisions': 0, 'range': None}
    origin = samples[0]['monotonic_ns']
    positions = [int((s['monotonic_ns'] - origin) / 1e9 // interval) for s in samples]
    end = max(positions)
    start = max(0, end - width + 1)
    bins = [[] for _ in range(end - start + 1)]
    counts = [0] * len(bins)
    for s, i in zip(samples, positions):
        if i < start:
            continue
        counts[i-start] += 1
        v = key(s)
        if number(v):
            bins[i-start].append(v)
    means = [math.fsum(b)/len(b) if b else None for b in bins]
    finite = [v for v in means if v is not None]
    lo, hi = (min(finite), max(finite)) if finite else (None, None)
    glyphs = ''
    for v, c in zip(means, counts):
        if c == 0:
            glyphs += '·'
        elif v is None:
            glyphs += '?'
        elif hi == lo:
            glyphs += '▄'
        else:
            glyphs += BARS[min(7, int(7*(v-lo)/(hi-lo)))]
    return {'glyphs': glyphs, 'missing_bins': sum(c == 0 for c in counts),
            'unknown_bins': sum(c > 0 and v is None for c, v in zip(counts, means)),
            'collisions': sum(max(0, c-1) for c in counts),
            'range': [lo, hi] if finite else None,
            'first_bin': start, 'last_bin': end, 'bin_seconds': interval}


def analyze(rows, snapshot_sha, byte_count, observed_as_of_utc=None):
    interval = rows[0]['payload'].get('interval_seconds')
    if not number(interval) or interval <= 0:
        raise ValueError('positive nominal interval required')
    samples = [r for r in rows if r['payload'].get('kind') == 'sample']
    gaps = [(b['monotonic_ns']-a['monotonic_ns'])/1e9 for a,b in zip(samples,samples[1:])]
    clock_differences = [((utc(b['observed_utc'])-utc(a['observed_utc'])).total_seconds() -
                          (b['monotonic_ns']-a['monotonic_ns'])/1e9)*1000
                         for a,b in zip(samples,samples[1:])]
    late = [r['payload'].get('schedule_lateness_seconds') for r in samples]
    def res(s): return s['payload'].get('resources', {})
    metrics = {
        'deadline_lateness_ms': lambda s: s['payload'].get('schedule_lateness_seconds', 0)*1000
            if number(s['payload'].get('schedule_lateness_seconds')) else None,
        'OS_available_memory_GiB': lambda s: (value(res(s), 'os_memory_view', 'MemAvailable_bytes')/2**30)
            if value(res(s), 'os_memory_view', 'MemAvailable_bytes') is not None else None,
        'workspace_available_GiB': lambda s: (value(res(s), 'workspace_filesystem', 'available_bytes')/2**30)
            if value(res(s), 'workspace_filesystem', 'available_bytes') is not None else None,
        'OS_load_1m': lambda s: value(res(s), 'load_1_5_15', 0),
    }
    # Include only observed cumulative self CPU counters with valid monotonic deltas.
    cpu_rates = []
    invalid_cpu_pairs = 0
    for a,b in zip(samples,samples[1:]):
        ca = res(a).get('observer_process', {})
        cb = res(b).get('observer_process', {})
        fields = ('cpu_user_seconds', 'cpu_system_seconds')
        if all(number(c.get(k)) for c in (ca, cb) for k in fields):
            delta = sum(cb[k]-ca[k] for k in fields)
            elapsed = (b['monotonic_ns']-a['monotonic_ns'])/1e9
            if delta >= 0 and elapsed > 0:
                cpu_rates.append(100*delta/elapsed)
            else:
                invalid_cpu_pairs += 1
        else:
            invalid_cpu_pairs += 1
    return {
        'schema': 1, 'run_id': rows[0]['run_id'], 'snapshot_sha256': snapshot_sha,
        'snapshot_bytes': byte_count, 'records': len(rows), 'samples': len(samples),
        'first_sample_utc': samples[0]['observed_utc'] if samples else None,
        'last_sample_utc': samples[-1]['observed_utc'] if samples else None,
        'nominal_interval_seconds': interval,
        'terminal_record_present': rows[-1]['payload'].get('kind') == 'stop',
        'snapshot_observed_as_of_utc': observed_as_of_utc,
        'last_sample_age_seconds_by_UTC': (utc(observed_as_of_utc)-utc(samples[-1]['observed_utc'])).total_seconds()
            if observed_as_of_utc and samples else None,
        'sample_interval_seconds': describe(gaps),
        'interval_excess_seconds': describe([x-interval for x in gaps]),
        'paired_clock_increment_difference_ms': describe(clock_differences),
        'declared_deadline_lateness_ms': describe([v*1000 for v in late if number(v)]),
        'intervals_exceeding_1_5_nominal': sum(g > 1.5*interval for g in gaps),
        'observer_CPU_percent_of_one_logical_CPU': describe(cpu_rates),
        'invalid_self_CPU_pairs': invalid_cpu_pairs,
        'metrics': {k: {'statistics': describe([f(s) for s in samples]),
                        'timeline': timeline(samples, interval, f)} for k,f in metrics.items()},
        'limits': [
            'A verified snapshot is evidence of observations, not current process liveness.',
            'Last-sample age is an as-of UTC comparison, not proof of a dead sampler; UTC steps can distort it.',
            'Record timestamps follow resource collection; declared lateness is measured before collection. These are different boundaries.',
            'Absent terminal record means lifetime is unresolved; no exact failure time inferred.',
            'UTC-minus-monotonic increments are clock disagreement, not absolute clock drift or synchronization accuracy.',
            'Deadline lateness uses the sampler target, which resets after overruns; it can conceal missed original-grid deadlines.',
            'Time bins are a visualization convention anchored at first sample; boundary jitter may cause collisions and empty bins.',
            'OS-exposed memory, CPU count and load are not established container allocation or model-serving resources.',
            'Self CPU is process accounting, not total observer cost; filesystem and tool overhead remain unmeasured.',
            'Nearest-rank empirical p95 is descriptive; small samples and serial dependence limit inference.',
            'Local hash consistency is not independently anchored authenticity.'
        ]}


def fmt(x):
    return 'unknown' if x is None else f'{x:.6g}'


def render(a):
    lines = ['╔════════════════════════════════════════════════════════════════════╗',
             '║                 THE OBSERVER OF THE HABITAT                       ║',
             '╚════════════════════════════════════════════════════════════════════╝',
             f"Run       {a['run_id']}", f"Samples   {a['samples']}  │  records {a['records']}",
             f"From      {a['first_sample_utc']}", f"Through   {a['last_sample_utc']}",
             f"Terminal  {'observed' if a['terminal_record_present'] else 'not observed; lifetime unresolved'}",
             f"As of     {a['snapshot_observed_as_of_utc'] or 'not supplied'}",
             f"Tail age  {fmt(a['last_sample_age_seconds_by_UTC'])} seconds by UTC",
             '', 'NOMINAL-TIME STRIPS · last ≤60 bins · one row-specific scale',
             '· empty bin   ? unobserved value   ▄ constant series   ▁→█ low→high']
    for k,m in a['metrics'].items():
        t=m['timeline']; rg=t['range']
        lines.extend([f'\n{k}', f"  {t['glyphs']}",
                      f"  scale {fmt(rg[0]) if rg else 'unknown'} … {fmt(rg[1]) if rg else 'unknown'}"
                      f" │ empty {t['missing_bins']} │ colliding samples {t['collisions']}"])
    lines += ['', 'INTERVAL DIAGNOSTICS · empirical nearest-rank summaries']
    for key in ('sample_interval_seconds','interval_excess_seconds','paired_clock_increment_difference_ms',
                'declared_deadline_lateness_ms','observer_CPU_percent_of_one_logical_CPU'):
        s=a[key]
        lines += [key, '  n=0' if not s['n'] else
                  f"  n={s['n']}  min={fmt(s['min'])}  median={fmt(s['median'])}  p95={fmt(s['p95'])}  max={fmt(s['max'])}"]
    lines += ['', 'INTERPRETATION GUARDRAILS'] + ['  '+x for x in a['limits']]
    lines += ['', 'Snapshot SHA-256  '+a['snapshot_sha256'], '']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot'); p.add_argument('--json', action='store_true'); p.add_argument('--as-of', help='Explicit UTC observation time; never inferred from filename')
    args=p.parse_args()
    rows, sha, size=load_snapshot(args.snapshot)
    result=analyze(rows,sha,size,args.as_of)
    print(json.dumps(result,indent=2,allow_nan=False) if args.json else render(result))

if __name__ == '__main__':
    main()
