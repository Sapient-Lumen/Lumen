"""One bounded paired local sample-cost study; no donor code or active-log writes."""
import sys, pathlib, json, time, hashlib, datetime, importlib.util, os
sys.dont_write_bytecode=True
p=pathlib.Path(__file__).parent
plan_bytes=(p/'PLAN.json').read_bytes();plan=json.loads(plan_bytes)
source=p.parents[1]/'habitat_observer.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()==plan['source_sha256']
spec=importlib.util.spec_from_file_location('observer_under_test',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
writers={k:mod.Writer(str(p/k), 'sample-cost-01-'+k,budget=262144) for k in ['minimal','full']}
start=time.monotonic_ns();cpu=time.process_time_ns();records=[];errors=[];stop='count_complete'
try:
 for pair in range(12):
  order=['minimal','full'] if pair%2==0 else ['full','minimal']
  for pos,kind in enumerate(order):
   if time.monotonic_ns()-start>10_000_000_000 or time.process_time_ns()-cpu>500_000_000:
    stop='budget_exhausted';break
   begin=time.monotonic_ns();cb=time.process_time_ns()
   payload={'kind':'sample','timestamp':mod.utc()}
   if kind=='full':payload.update(resources=mod.resources(),project_receipts=mod.project_observations())
   collected=time.monotonic_ns();cc=time.process_time_ns()
   row=writers[kind].append(payload)
   ca=time.process_time_ns();end=time.monotonic_ns()
   records.append({'pair':pair,'position':pos,'condition':kind,'begin_monotonic_ns':begin,'end_monotonic_ns':end,'elapsed_ns':end-begin,'process_cpu_ns':ca-cb,'collection_elapsed_ns':collected-begin,'append_elapsed_ns':end-collected,'collection_cpu_ns':cc-cb,'append_cpu_ns':ca-cc,'row_sha256':writers[kind].previous,'row_sequence':row['sequence']})
  if stop!='count_complete':break
except Exception as e:
 stop='error';errors.append({'type':type(e).__name__})
measured_end=time.monotonic_ns();measured_cpu=time.process_time_ns()
seal_begin=time.monotonic_ns()
for w in writers.values():w.seal()
seal_end=time.monotonic_ns()
result={'experiment_id':'sample-cost-01','written_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_sha256':hashlib.sha256(plan_bytes).hexdigest(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'collector_sha256':plan['source_sha256'],'stop':stop,'errors':errors,'records':records,'study_loop_elapsed_ns':measured_end-start,'study_loop_cpu_ns':measured_cpu-cpu,'final_sealing_elapsed_ns':seal_end-seal_begin,'ledger_bytes':{k:w.bytes for k,w in writers.items()},'qualification':'Per-sample brackets omit setup, scheduling, final seal and result write. Same source functions and Writer, not an exact replay of the active collector loop.'}
raw=(json.dumps(result,indent=2)+'\n').encode();assert len(raw)<=65536
with (p/'RESULT.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert (p/'RESULT.json').read_bytes()==raw
print(json.dumps({'stop':stop,'samples':len(records),'loop_elapsed_ns':result['study_loop_elapsed_ns'],'loop_cpu_ns':result['study_loop_cpu_ns'],'result_sha256':hashlib.sha256(raw).hexdigest()}))
