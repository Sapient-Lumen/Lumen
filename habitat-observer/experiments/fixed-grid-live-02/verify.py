from pathlib import Path
import json,hashlib,statistics,datetime
p=Path(__file__).parent;plan=json.loads((p/'PLAN.json').read_text());b=(p/'run/segment-0001.jsonl').read_bytes();lines=b.splitlines(keepends=True);rows=[json.loads(x) for x in lines];previous='0'*64
for n,(line,row) in enumerate(zip(lines,rows),1):
 assert row['sequence']==n and row['previous_sha256']==previous;previous=hashlib.sha256(line).hexdigest()
assert rows[0]['payload']['source_sha256']==plan['source_sha256']
manifest=json.loads((p/'run/manifest.json').read_text());assert manifest['sealed_segments'][0]['sha256']==hashlib.sha256(b).hexdigest()
samples=[r for r in rows if r['payload']['kind']=='sample'];stop=rows[-1]['payload'];assert stop['kind']=='stop' and stop['reason']=='duration_complete'
assert stop['slots_due_at_stop']==stop['sampled_slots']+stop['missed_slots_total']==plan['expected_slots'];assert stop['future_slots_not_observed']==0;assert len(samples)==stop['sampled_slots'];assert [r['payload']['scheduled_slot'] for r in samples]==list(range(10))
costs=[]
for i,row in enumerate(rows[2:],2):
 m=row['payload']['previous_sample_measurement'];assert m['row_sha256']==hashlib.sha256(lines[i-1]).hexdigest() and m['sequence']==i
 assert m['elapsed_ns']==m['collection_elapsed_ns']+m['append_elapsed_ns'];assert m['elapsed_ns']>=0 and m['process_cpu_ns']>=0;costs.append(m)
def stats(v):return {'n':len(v),'min':min(v),'median':statistics.median(v),'max':max(v)}
review={'reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':rows[0]['run_id'],'start_utc':rows[0]['observed_utc'],'terminal_utc':rows[-1]['observed_utc'],'ledger_sha256':hashlib.sha256(b).hexdigest(),'samples':len(samples),'missed_slots':stop['missed_slots_total'],'all_due_slots_accounted':True,'all_completed_costs_bound':len(costs)==len(samples),'elapsed_sample_cost_ns':stats([m['elapsed_ns'] for m in costs]),'CPU_sample_cost_ns':stats([m['process_cpu_ns'] for m in costs]),'slot_lateness_seconds':stats([r['payload']['schedule_lateness_seconds'] for r in samples]),'cgroup_unknown_samples':sum(r['payload']['resources']['cgroup']['status']=='unknown' for r in samples),'qualification':'One ten-minute trial; no long-run uptime, population tail or causal comparison with the earlier burst study. Existing collector untouched.'}
(p/'ROOT-REVIEW.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review,indent=2))
