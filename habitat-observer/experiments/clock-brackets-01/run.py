"""Bounded read-only clock comparison; output is the sole experiment write."""
import time,json,datetime,hashlib,os
from pathlib import Path
p=Path(__file__).parent
plan=(p/'PLAN.json').read_bytes()
start=time.monotonic_ns();cpu=time.process_time_ns()
readers={'monotonic_control':time.monotonic_ns,'realtime':time.time_ns}
unsupported=[]
for name,constant in [('monotonic_raw','CLOCK_MONOTONIC_RAW'),('boottime','CLOCK_BOOTTIME')]:
 if hasattr(time,constant):readers[name]=lambda c=getattr(time,constant):time.clock_gettime_ns(c)
 else:unsupported.append(name)
records=[];errors=[];reason='count_complete'
for cycle in range(24):
 order=list(readers)
 if cycle%2:order.reverse()
 for name in order:
  if (time.monotonic_ns()-start)>10_000_000_000 or (time.process_time_ns()-cpu)>250_000_000:
   reason='budget_stop';break
  try:
   before=time.monotonic_ns();value=readers[name]();after=time.monotonic_ns()
   if after<before:raise ValueError('monotonic_regression')
   if name=='monotonic_control' and not before<=value<=after:raise ValueError('control_outside_bracket')
   records.append({'cycle':cycle,'clock':name,'before_ns':before,'value_ns':value,'after_ns':after,'width_ns':after-before,'offset_lower_ns':value-after,'offset_upper_ns':value-before})
  except (OSError,ValueError) as e:
   errors.append({'clock':name,'type':type(e).__name__});reason='measurement_error';break
 if reason!='count_complete':break
 if cycle<23:time.sleep(.02)
end=time.monotonic_ns();end_cpu=time.process_time_ns()
summary={}
for name in readers:
 r=[x for x in records if x['clock']==name]
 if r:
  lo=max(x['offset_lower_ns'] for x in r);hi=min(x['offset_upper_ns'] for x in r)
  summary[name]={'n':len(r),'constant_offset_compatible':lo<=hi,'intersection_lower_ns':lo,'intersection_upper_ns':hi,'width_min_ns':min(x['width_ns'] for x in r),'width_max_ns':max(x['width_ns'] for x in r)}
result={'schema':1,'experiment_id':'clock-brackets-01','written_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_sha256':hashlib.sha256(plan).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'elapsed_ns':end-start,'process_cpu_ns':end_cpu-cpu,'reason':reason,'unsupported':unsupported,'errors':errors,'clock_metadata':{name:vars(time.get_clock_info(name)) for name in ['time','monotonic','process_time']},'summary':summary,'records':records,'qualification':'Single short local episode. Paired-clock compatibility is not external calibration or absolute accuracy.'}
raw=(json.dumps(result,indent=2)+'\n').encode();assert len(raw)<=65536
with (p/'RESULT.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert (p/'RESULT.json').read_bytes()==raw
print(json.dumps({'summary':summary,'reason':reason,'elapsed_ns':end-start,'process_cpu_ns':end_cpu-cpu,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
