"""One real-run evaluation, with explicit pending states and no simulated measurements."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from riwaq import (CampusApp, MeteredClient, configured_client, JudgeVerdict, PROMPTS,
                   output_guard, mask_data, ModelError)
from evidence import (run_golden, regression_gate, cohen_kappa, break_even,
                      safety_tests, fault_drills, privacy_report, guard_report)
from backends import configuration, qwen


def meter_summary(logs):
    ok = [r for r in logs if r['status']=='ok']
    verified = bool(ok) and all(r.get('usage_verified') for r in ok)
    total = sum(r.get('input_tokens',0) for r in ok)
    return {'attempts':len(logs), 'successful_calls':len(ok), 'usage_verified':verified,
            'cost_usd':sum(r['cost_usd'] for r in logs) if logs and all(r.get('cost_usd') is not None for r in logs) else None,
            'provider_input_tokens':total if verified else None,
            'provider_cached_ratio':sum(r.get('cached_input_tokens',0) for r in ok)/total
            if total and verified and all(r.get('cached_usage_observed') for r in ok) else None}


def cache_replay(factory, cases):
    questions = [c for c in cases if c['intent']=='faq']
    rows = []
    for enabled in (False, True):
        client = factory(); app = CampusApp(client, cache=enabled)
        start = time.perf_counter(); correct = 0
        for _ in range(2):
            for case in questions:
                result = app.respond(case['text'])
                correct += result.get('answer')==case['answer'] and result.get('source_id')==case['source_id']
        seconds = time.perf_counter()-start
        rows.append({'step':'response cache' if enabled else 'no cache', 'requests':len(questions)*2,
                     'seconds':seconds, 'mean_latency_ms':1000*seconds/(len(questions)*2),
                     'quality':correct/(len(questions)*2), 'meter':meter_summary(client.logs), 'usage':client.logs})
    return rows


def judge_calibration(root, factory):
    artifact = json.loads((root/'data/judge-calibration.v1.json').read_text())
    labels = artifact['rows']; client = factory(); predictions = []; errors = 0
    for row in labels:
        try:
            reply = client.complete('judge.v1', {'answer':row['answer'],'reference':row['reference']},64)
            predictions.append(JudgeVerdict.model_validate_json(reply.text).supported)
        except (ModelError, ValueError):
            predictions.append(None); errors += 1
    expected = [r['supported'] for r in labels]
    kappa = cohen_kappa(expected, predictions)
    reviewed = all(r.get('owner_approved') is True and r.get('reviewer') and r.get('reviewed_at') for r in labels)
    return {'dimension':'factual support', 'n':len(labels), 'kappa':kappa,
            'agreement':sum(a==b for a,b in zip(expected,predictions))/len(labels), 'invalid_verdicts':errors,
            'label_provenance':artifact['provenance'], 'human_reviewed':reviewed,
            'qualified':bool(reviewed and not errors and kappa is not None and kappa>=.6),
            'predictions':predictions, 'usage':client.logs}


def write_report(root, result):
    lines = ['# Riwaq evaluation report', '', 'Run UTC: '+result['run_utc'], '',
             'Only completed real inference is reported below. Missing work is pending.', '',
             '## Deterministic checks', '', json.dumps(result.get('checks',{})), '',
             '## Same golden set, by slice', '', '| Backend | Slice | N | Pass rate |', '|---|---|---:|---:|']
    for name, data in result['backends'].items():
        for label, row in data['evaluation']['slices'].items():
            lines.append(f"| {name} | {label} | {row['n']} | {row['rate']:.1%} |")
    lines += ['', '## Cost and latency before/after', '',
              '| Backend | Step | Requests | Model calls | Mean ms | USD | Quality | Cached input ratio |',
              '|---|---|---:|---:|---:|---|---:|---|']
    for name, data in result['backends'].items():
        for row in data['cache']:
            m=row['meter']; cost=m['cost_usd']
            if name=='open_weight': cost=row['seconds']/3600*result['hardware_hourly_usd']
            lines.append(f"| {name} | {row['step']} | {row['requests']} | {m['attempts']} | {row['mean_latency_ms']:.2f} | {cost} | {row['quality']:.1%} | {m['provider_cached_ratio']} |")
    lines += ['', 'Qwen USD is modeled occupied time × assumed $1/hour; Hosted API USD estimates use recorded Hugging Face catalog rates before credits, not the previous GPT rates. '
              'Unknown API error charges remain unknown. Absent cached-token fields are not evidence of zero cache hits.', '',
              '## Judge, throughput, break-even and gates', '', '```json',
              json.dumps({'judge':{k:v for k,v in result.get('judge',{}).items() if k!='usage'}, **{k:v for k,v in result.items() if k not in ('backends','checks','judge')}},ensure_ascii=False,indent=2), '```', '',
              'Serial warmed Qwen FAQ throughput excludes startup and guard-only requests. It is workload throughput, '
              'not saturated GPU capacity. Hardware cost is an explicit assumption; compare quality before choosing a backend. '
              'Exact-grounding checks deliberately reject paraphrases. Calibration fixtures are not independent human labels until reviewed.', '',
              'Per-call tokens, cost, latency, prompt hashes and backend identity are in `run-results.json`. '
              'Regression baseline is the committed development reference; it is never automatically promoted.']
    (root/'EVALUATION_REPORT.md').write_text('\n'.join(lines)+'\n')
    (root/'run-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


def run(root):
    root=Path(root); config=configuration()
    result={'run_utc':datetime.now(timezone.utc).isoformat(), 'hardware_hourly_usd':config['hardware_hourly_usd'],
            'backends':{}, 'pending':[], 'gates':{}, 'configuration':config,
            'prompt_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'prompts').glob('*.json')}}
    cases=json.loads((root/'data/golden.v1.json').read_text())
    seeds=json.loads((root/'data/seeds.json').read_text())
    checks=safety_tests(); fault_drills(); privacy=privacy_report(root); guard=guard_report(seeds)
    assert guard['block_rate']==1 and guard['false_positive_rate']==0
    result['pending'].append('Independent review of data/judge-calibration.v1.json') if not all(r.get('owner_approved') and r.get('reviewer') and r.get('reviewed_at') for r in json.loads((root/'data/judge-calibration.v1.json').read_text())['rows']) else None
    result['checks']={'safety_assertions':len(checks),'privacy':privacy,'bilingual_injection':guard}
    write_report(root,result)
    for alias in ('hosted','open_weight'):
        print('Running',alias,flush=True)
        try:
            # Resolve once: repeated cases must not reload weights or create SDK transports.
            base=configured_client(alias)
            factory=lambda: MeteredClient(base.primary,base.fallback)
            if alias=='open_weight':
                result['qwen_provenance']=base.primary.provenance
                warmup=factory()
                warmup.complete('faq.v1',{'text':'transcript fee','language':'en','source':__import__('riwaq').CATALOG['transcript']},256)
                result['qwen_warmup_usage']=warmup.logs
            evaluation=run_golden(cases,client_factory=factory)
            result['backends'][alias]={'evaluation':evaluation,'cache':[]}
            result['gates'][alias]=regression_gate(root/'data/baseline.v1.json',evaluation)
            result['backends'][alias]['cache']=cache_replay(factory,cases)
            cache=result['backends'][alias]['cache']
            result['gates'][alias]['cache_quality_preserved']=cache[1]['quality']>=cache[0]['quality']
            result['gates'][alias]['allowed'] &= result['gates'][alias]['cache_quality_preserved']
            if alias=='open_weight':
                before=cache[0]
                result['qwen_throughput']={'requests_per_second':before['requests']/before['seconds'],
                    'output_tokens_per_second':sum(x.get('output_tokens',0) for x in before['usage'])/before['seconds'],
                    'all_calls_succeeded':all(x['status']=='ok' for x in before['usage']), 'quality':before['quality']}
            else:
                result['judge']=judge_calibration(root,factory)
        except Exception as exc:
            # Never serialize SDK exception bodies or secrets.
            result['pending'].append(alias+': '+type(exc).__name__+' (HF_TOKEN required for hosted; compatible PyTorch/Transformers and model access required for Qwen)')
        write_report(root,result)
    if len(result['backends'])==2 and result.get('qwen_throughput',{}).get('all_calls_succeeded'):
        result['break_even']={}
        for row in result['backends']['hosted']['cache']:
            cost=row['meter']['cost_usd']
            if cost and config['hardware_hourly_usd']:
                result['break_even'][row['step']]=break_even(config['hardware_hourly_usd'],result['qwen_throughput']['requests_per_second'],cost/row['requests'])
    if not result.get('break_even'): result['pending'].append('Measured self-host break-even unavailable')
    result['regression_allowed']=len(result['gates'])==2 and all(x['allowed'] for x in result['gates'].values())
    result['complete']=not result['pending'] and len(result['backends'])==2
    write_report(root,result)
    return result
