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
            'provider_cached_ratio':sum(r.get('cached_input_tokens',0) for r in successes)/token_total if verified and token_total else None,
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
                     'language':c['language'],'supported':None,'owner_approved':False})
        altered=c['answer']+' '+('Additional fee: 700 SAR.' if c['language']=='en' else 'رسوم إضافية: 700 ريال.')
        rows.append({'id':c['id']+'-altered','answer':altered,'reference':c['answer'],
                     'language':c['language'],'supported':None,'owner_approved':False})
    return rows
