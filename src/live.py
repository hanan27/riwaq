"""Optional paid/live experiments. Never invoked by default notebook execution."""
import json
import os
import statistics
import time
from pathlib import Path
from riwaq import *
from evidence import run_golden, regression_gate, extraction_report, break_even, calibrate_judge


def meter_summary(logs):
    successes = [r for r in logs if r['status']=='ok']
    token_total = sum(r.get('input_tokens',0) for r in successes)
    # Unknown usage/cost is not zero cost. Error responses can also be chargeable.
    known_cost = bool(logs) and all(r.get('cost_usd') is not None for r in logs)
    verified = bool(successes) and all(r.get('usage_verified') for r in successes)
    return {'attempts':len(logs), 'successful_calls':len(successes),
            'cost_usd':sum(r['cost_usd'] for r in logs) if known_cost else None,
            'provider_input_tokens':token_total if verified else None,
            'provider_cached_ratio':sum(r.get('cached_input_tokens',0) for r in successes)/token_total if verified and token_total and all(r.get('cached_usage_observed') for r in successes) else None,
            'usage_verified':verified}


def live_comparison(cases, seeds, root):
    results={}
    for name in ('commercial','open_weight'):
        # Check config before any potentially billable call.
        configured_client(name)
    for name in ('commercial','open_weight'):
        start=time.perf_counter()
        evaluation=run_golden(cases,client_factory=lambda:configured_client(name))
        duration=time.perf_counter()-start
        timings=sorted(r['latency_ms'] for r in evaluation['rows'])
        results[name]={'evaluation':evaluation,'meter_summary':meter_summary(evaluation['meter']),
                       'wall_seconds':duration, 'pipeline_requests_per_second':len(cases)/duration,
                       'latency_p50_ms':statistics.median(timings),'latency_p95_ms':timings[min(len(timings)-1,int(.95*len(timings)))],
                       'extraction':extraction_report(seeds,factory=lambda:configured_client(name))}
    (Path(root)/'live_evidence.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    record_comparison(root,results)
    return results


def live_cache_replay(cases, seeds, backend='commercial'):
    rows=[]
    for enabled in (False,True):
        client=configured_client(backend)
        app=CampusApp(client,cache=enabled)
        for _ in range(5):
            for text,key in seeds['faq_ar']+seeds['faq_en']:
                result=app.respond(text)
                assert result.get('answer')==CATALOG[key][language(text)], 'quality failed during cost replay'
        evaluation=run_golden(cases,client_factory=lambda:configured_client(backend),cache=enabled)
        rows.append({'step':'exact cache' if enabled else 'baseline','requests':100,
                     **meter_summary(client.logs),'eval':evaluation['slices']})
    baseline,after=rows[0]['cost_usd'],rows[1]['cost_usd']
    return {'rows':rows,'cost_reduction':1-after/baseline if baseline and after is not None else None}


def measure_self_host(cases):
    # Measure actual model work, excluding guard-only cases from the throughput numerator.
    client=configured_client('open_weight')
    faq=[c for c in cases if c['intent']=='faq']
    start=time.perf_counter()
    for c in faq:
        result=CampusApp(client).respond(c['text'])
        assert result.get('answer')==c['answer'], 'self-host quality failure'
    elapsed=time.perf_counter()-start
    assert all(r['status']=='ok' for r in client.logs), 'retry-contaminated throughput run'
    return {'model_requests':len(client.logs),'seconds':elapsed,'measured_rps':len(client.logs)/elapsed,
            'scope':'serial FAQ on configured open-weight endpoint; valid as GPU throughput only if this endpoint is your isolated self-host',
            'meter':meter_summary(client.logs)}


def hosting_comparisons(hourly_usd, measured_rps, replay, utilization=.5):
    out={}
    for r in replay['rows']:
        if r['cost_usd'] is None or r['cost_usd']<=0: raise ValueError('verified positive API cost required')
        out[r['step']]=break_even(hourly_usd,measured_rps,r['cost_usd']/r['requests'],utilization)
    return out


def judge_candidates(cases):
    rows=[]
    for c in [r for r in cases if r['intent']=='faq']:
        rows.append({'id':c['id']+'-source','answer':c['answer'],'reference':c['answer'],
                     'language':c['language'],'supported':None,'owner_approved':False,'reviewer':None,'reviewed_at':None})
        altered=c['answer']+' '+('Additional fee: 700 SAR.' if c['language']=='en' else 'رسوم إضافية: 700 ريال.')
        rows.append({'id':c['id']+'-altered','answer':altered,'reference':c['answer'],
                     'language':c['language'],'supported':None,'owner_approved':False,'reviewer':None,'reviewed_at':None})
    return rows


def record_section(root, filename, title, text):
    path=Path(root)/filename
    start,end=f'<!-- BEGIN {title} -->',f'<!-- END {title} -->'
    current=path.read_text() if path.exists() else '# Riwaq evidence\n'
    if start in current:
        before,remaining=current.split(start,1)
        _,after=remaining.split(end,1)
        current=before+after
    path.write_text(current.rstrip()+'\n\n'+start+'\n\n## '+title+'\n\n'+text+'\n\n'+end+'\n')


def record_comparison(root,results):
    text='These live results are separate from the offline simulator baseline. Unknown prices or missing provider usage remain unknown.\n\n'
    text+='| Backend | Slice | Cases | Pass rate |\n|---|---|---:|---:|\n'
    for backend,result in results.items():
        for label,slice_result in result['evaluation']['slices'].items():
            text+=f"| {backend} | {label} | {slice_result['n']} | {slice_result['rate']:.1%} |\n"
    text+='\n| Backend | p50 ms | p95 ms | Measured inference cost USD | Cached input ratio |\n|---|---:|---:|---|---|\n'
    for backend,result in results.items():
        meter=result['meter_summary']
        text+=f"| {backend} | {result['latency_p50_ms']:.2f} | {result['latency_p95_ms']:.2f} | {meter['cost_usd']} | {meter['provider_cached_ratio']} |\n"
    text+='\nLimitations: measured on the versioned development set; no independent holdout or human-label approval is implied. SDK transport, provider time and local guards contribute to latency. Pricing must be supplied from verified account rates.\n'
    record_section(root,'EVALUATION_REPORT.md','Live backend comparison',text)
    record_section(root,'BENCHMARKS.md','Live backend comparison',text)


def record_calibration(root,calibration):
    (Path(root)/'judge_calibration.json').write_text(json.dumps(calibration,indent=2)+'\n')
    record_section(root,'EVALUATION_REPORT.md','Human-labelled judge calibration',
        'Rubric: `eval/rubrics/groundedness.v1.md`; single dimension: factual support.\n\n'+
        '```json\n'+json.dumps(calibration,indent=2)+'\n```\nSafety continues to use deterministic checks only.')


def record_economics(root,replay,throughput,comparisons):
    text='| Step | Requests | USD | Overall eval | Safety eval | Cached input ratio |\n|---|---:|---|---:|---:|---|\n'
    for row in replay['rows']:
        text+=f"| {row['step']} | {row['requests']} | {row['cost_usd']} | {row['eval']['overall']['rate']:.1%} | {row['eval']['risk=safety']['rate']:.1%} | {row['provider_cached_ratio']} |\n"
    text+='\nCost reduction: '+str(replay['cost_reduction'])+'\n\nMeasured serial self-host run and both comparisons:\n```json\n'+json.dumps({'throughput':throughput,'comparisons':comparisons},indent=2)+'\n```'
    record_section(root,'BENCHMARKS.md','Measured economics',text)
    record_section(root,'EVALUATION_REPORT.md','Measured economics',text)
