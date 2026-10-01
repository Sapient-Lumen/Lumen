import pathlib,json,hashlib,statistics,datetime
p=pathlib.Path(__file__).parent;r=json.loads((p/'RESULT.json').read_text());assert r['stop']=='count_complete' and not r['errors'] and len(r['records'])==24
for name in ['minimal','full']:
 data=(p/name/'segment-0001.jsonl').read_bytes();lines=data.splitlines(keepends=True);assert len(lines)==12;prev='0'*64
 for seq,line in enumerate(lines,1):
  row=json.loads(line);assert row['sequence']==seq and row['previous_sha256']==prev;prev=hashlib.sha256(line).hexdigest()
  record=next(x for x in r['records'] if x['condition']==name and x['row_sequence']==seq);assert record['row_sha256']==prev
 manifest=json.loads((p/name/'manifest.json').read_text());assert manifest['sealed_segments'][0]['sha256']==hashlib.sha256(data).hexdigest()
summary={}
for name in ['minimal','full']:
 rs=[x for x in r['records'] if x['condition']==name];summary[name]={}
 for key in ['elapsed_ns','process_cpu_ns','collection_elapsed_ns','append_elapsed_ns']:
  vals=[x[key] for x in rs];summary[name][key]={'min':min(vals),'median':statistics.median(vals),'max':max(vals)}
pairs=[]
for i in range(12):
 a={x['condition']:x for x in r['records'] if x['pair']==i};assert len(a)==2
 pairs.append({'pair':i,'first':next(x['condition'] for x in a.values() if x['position']==0),'full_minus_minimal_elapsed_ns':a['full']['elapsed_ns']-a['minimal']['elapsed_ns'],'full_minus_minimal_cpu_ns':a['full']['process_cpu_ns']-a['minimal']['process_cpu_ns']})
review={'reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result_sha256':hashlib.sha256((p/'RESULT.json').read_bytes()).hexdigest(),'ledgers_hashes_sequences_and_record_links_verified':True,'budgets_met':r['study_loop_elapsed_ns']<=10_000_000_000 and r['study_loop_cpu_ns']<=500_000_000 and all(v<=262144 for v in r['ledger_bytes'].values()),'summary':summary,'pairs':pairs,'paired_median_elapsed_delta_ns':statistics.median(x['full_minus_minimal_elapsed_ns'] for x in pairs),'paired_median_cpu_delta_ns':statistics.median(x['full_minus_minimal_cpu_ns'] for x in pairs),'full_cpu_greater_pairs':sum(x['full_minus_minimal_cpu_ns']>0 for x in pairs),'full_elapsed_greater_pairs':sum(x['full_minus_minimal_elapsed_ns']>0 for x in pairs),'limits':['One warm clustered local episode; no population inference','Minimal and full payloads differ in size and work; cannot isolate one cause','fsync and readback success are not proof of persistence across host power loss','Active collector scheduling and whole tool transport excluded']}
(p/'ROOT-REVIEW.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review,indent=2))
