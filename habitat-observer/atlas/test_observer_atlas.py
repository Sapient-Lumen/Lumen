import hashlib,json,tempfile,unittest
from pathlib import Path
import observer_atlas as a

class AtlasTests(unittest.TestCase):
    def encoded(self, rows):
        raw=b''; prev='0'*64
        for i,r in enumerate(rows,1):
            row=dict(schema=1,sequence=i,run_id='fixture',previous_sha256=prev,**r)
            line=(json.dumps(row)+'\n').encode();raw+=line;prev=hashlib.sha256(line).hexdigest()
        return raw
    def row(self,t,kind='sample',**payload):
        return dict(monotonic_ns=(t+1)*10**9,observed_utc=f'2026-10-01T00:{t//60:02d}:{t%60:02d}+00:00',payload=dict(kind=kind,**payload))
    def load(self,raw):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'snapshot';p.write_bytes(raw)
            return a.load_snapshot(p)
    def test_verified_chain_and_no_terminal_claim(self):
        rows,sha,size=self.load(self.encoded([self.row(0,'start',interval_seconds=60),self.row(1),self.row(61)]))
        result=a.analyze(rows,sha,size)
        self.assertEqual(result['sample_interval_seconds']['median'],60)
        self.assertFalse(result['terminal_record_present'])
        self.assertEqual(result['metrics']['OS_load_1m']['statistics']['n'],0)
    def test_tampering_rejected(self):
        raw=self.encoded([self.row(0,'start',interval_seconds=60),self.row(1)])
        with self.assertRaises(ValueError):self.load(raw.replace(b'60',b'61',1))
    def test_truncated_rejected(self):
        with self.assertRaises(ValueError):self.load(self.encoded([self.row(0,'start')])[:-1])
    def test_nonmonotonic_rejected(self):
        with self.assertRaises(ValueError):self.load(self.encoded([self.row(0,'start'),self.row(0)]))
    def test_timezone_required(self):
        with self.assertRaises(ValueError):a.utc('2026-10-01T00:00:00')
    def test_sparse_gaps_not_zero(self):
        rows=[dict(monotonic_ns=x*10**9,v=y) for x,y in [(0,3),(180,9)]]
        t=a.timeline(rows,60,lambda r:r['v'])
        self.assertEqual(t['glyphs'],'▁··█');self.assertEqual(t['missing_bins'],2)
    def test_unknown_distinct_from_gap(self):
        rows=[dict(monotonic_ns=0,v=None),dict(monotonic_ns=120*10**9,v=0)]
        self.assertEqual(a.timeline(rows,60,lambda r:r['v'])['glyphs'],'?·▄')
    def test_collision_exposed(self):
        rows=[dict(monotonic_ns=x*10**9,v=x) for x in (0,30,60)]
        self.assertEqual(a.timeline(rows,60,lambda r:r['v'])['collisions'],1)
    def test_width_bound(self):
        rows=[dict(monotonic_ns=x*10**9,v=x) for x in (0,60000)]
        self.assertEqual(len(a.timeline(rows,60,lambda r:r['v'])['glyphs']),60)
    def test_quantiles_small_n(self):
        self.assertEqual(a.describe([1,2])['p95'],2)
        self.assertEqual(a.describe([None,float('nan'),True])['n'],0)
    def test_clock_disagreement_not_drift(self):
        rows=[self.row(0,'start',interval_seconds=60),self.row(1),self.row(61)]
        rows[-1]['observed_utc']='2026-10-01T00:01:02+00:00'
        r,sha,size=self.load(self.encoded(rows))
        self.assertAlmostEqual(a.analyze(r,sha,size)['paired_clock_increment_difference_ms']['median'],1000)
    def test_invalid_cpu_reset_exposed(self):
        rows=[self.row(0,'start',interval_seconds=60)]
        for t,c in [(1,5),(61,2)]:
            rows.append(self.row(t,resources={'observer_process':{'cpu_user_seconds':c,'cpu_system_seconds':0}}))
        r,sha,size=self.load(self.encoded(rows));v=a.analyze(r,sha,size)
        self.assertEqual(v['invalid_self_CPU_pairs'],1)
        self.assertEqual(v['observer_CPU_percent_of_one_logical_CPU']['n'],0)
    def test_render_unicode_and_limits(self):
        r,sha,size=self.load(self.encoded([self.row(0,'start',interval_seconds=60)]))
        text=a.render(a.analyze(r,sha,size));self.assertIn('THE OBSERVER',text);self.assertIn('lifetime unresolved',text)

if __name__=='__main__':unittest.main()
