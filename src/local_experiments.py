"""Reproducible local-model experiments; never substitute simulator numbers for weights."""
import hashlib
import json
import math
import statistics
import time
import zipfile
from pathlib import Path
from riwaq import CampusApp, configured_client, CATALOG, language
from evidence import run_golden, regression_gate, extraction_report, calibrate_judge, break_even
from live import meter_summary, record_section, record_calibration, judge_candidates


def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def run_local_evaluation(root,provenance,factory=None):
    root=Path(root)
    cases=json.loads((root/'data/golden.json').read_text())
    seeds=json.loads((root/'data/seeds.json').read_text())
    factory=factory or (lambda:configured_client('open_weight'))
    print('Evaluating real model on all',len(cases),'frozen cases...',flush=True)
    start=time.perf_counter()
    evaluation=run_golden(cases,client_factory=factory)
    elapsed=time.perf_counter()-start
    gate=regression_gate(root/'data/baseline.v1.json',evaluation)
    result={'provenance':provenance,'evaluation':evaluation,'gate_against_committed_baseline':gate,
            'wall_seconds':elapsed,'meter':meter_summary(evaluation['meter']),
            'extraction':extraction_report(seeds,factory=factory),
            'safety_green':evaluation['slices']['risk=safety']['rate']==1,
            'commercial_backend':{'status':'not run; no commercial access or documented alternative provided'}}
    write_json(root/'local_evaluation.json',result)
    table='| Slice | Cases | Passed | Rate |\n|---|---:|---:|---:|\n'
    for name,row in evaluation['slices'].items():table+=f"| {name} | {row['n']} | {row['passed']} | {row['rate']:.1%} |\n"
    failures=[row for row in evaluation['rows'] if not row['pass']]
    text='Actual local open-weight run. Model/hardware provenance:\n```json\n'+json.dumps(provenance,indent=2)+'\n```\n\n'+table
    text+='\nGate against the committed simulator baseline: `'+json.dumps(gate)+'`. A rejected gate remains rejected; no expectations were changed.\n'
    text+='\nExtraction by language:\n```json\n'+json.dumps(result['extraction'],indent=2)+'\n```\n'
    text+='\nFailed case IDs: '+(', '.join(row['id'] for row in failures) or 'none')+'.\n'
    text+='\nLimitations: this is one open-weight model, not a commercial-versus-open-weight comparison. Exact-source output checks reject paraphrases; a small model may underperform, especially in Arabic and tool selection. No human approval or calibrated judge is inferred.\n'
    record_section(root,'EVALUATION_REPORT.md','Local Hugging Face evaluation',text)
    record_section(root,'BENCHMARKS.md','Local Hugging Face evaluation',text)
    print('Local slices:',json.dumps(evaluation['slices'],indent=2),flush=True)
    print('Gate:',gate,'Safety green:',result['safety_green'],flush=True)
    return result


def local_cache_experiment(root,factory=None,hourly_usd=None,repeats=3):
    root=Path(root)
    if type(repeats) is not int or repeats<2:raise ValueError('Replay needs at least two repetitions')
    if hourly_usd is not None and (not math.isfinite(hourly_usd) or hourly_usd<0):raise ValueError('Hourly rate must be nonnegative and finite')
    factory=factory or (lambda:configured_client('open_weight'))
    seeds=json.loads((root/'data/seeds.json').read_text())
    cases=json.loads((root/'data/golden.json').read_text())
    questions=seeds['faq_ar']+seeds['faq_en']
    steps=[]
    for cache_on in (False,True):
        app=CampusApp(factory(),cache=cache_on)
        verdicts=[]
        start=time.perf_counter()
        for _ in range(repeats):
            for text,key in questions:
                response=app.respond(text)
                verdicts.append(response.get('answer')==CATALOG[key][language(text)] and response.get('source_id')==CATALOG[key]['id'])
        elapsed=time.perf_counter()-start
        # Full pipeline safety/quality verdict next to this optimization step, outside timed replay.
        evaluation=run_golden(cases,client_factory=factory,cache=cache_on)
        row={'step':'exact response cache' if cache_on else 'no response cache',
             'requests':len(verdicts),'elapsed_seconds':elapsed,'replay_pass_rate':sum(verdicts)/len(verdicts),
             'meter':meter_summary(app.client.logs),'eval':evaluation['slices'],
             'hourly_rate_input_usd':hourly_usd,
             'modeled_compute_cost_usd':elapsed/3600*hourly_usd if hourly_usd is not None else None,
             'cost_basis':'Measured occupied wall time × user-supplied hourly rate; not a provider invoice. Startup, idle and amortization excluded.',
             'usage':app.client.logs}
        steps.append(row)
    original,optimized=[row['modeled_compute_cost_usd'] for row in steps]
    reduction=1-optimized/original if original and optimized is not None else None
    result={'steps':steps,'modeled_cost_reduction':reduction,
            'quality_preserved':steps[1]['replay_pass_rate']>=steps[0]['replay_pass_rate'] and all(
                steps[1]['eval'][k]['rate']>=v['rate'] for k,v in steps[0]['eval'].items()),
            'prompt_cache_note':'Server prefix caching is enabled in both rows. Only returned cached_tokens counts as observed evidence; absent details remain unknown.'}
    write_json(root/'local_cache.json',result)
    text='Both steps use the actual local model. No paid API is needed. Dollar amounts are unknown unless an hourly rate is explicitly supplied.\n\n'
    text+='| Step | Requests | Model calls | Wall seconds | Replay quality | Full eval | Safety | Observed cached input ratio | Modeled USD |\n|---|---:|---:|---:|---:|---:|---:|---|---|\n'
    for row in steps:
        text+=f"| {row['step']} | {row['requests']} | {row['meter']['attempts']} | {row['elapsed_seconds']:.3f} | {row['replay_pass_rate']:.1%} | {row['eval']['overall']['rate']:.1%} | {row['eval']['risk=safety']['rate']:.1%} | {row['meter']['provider_cached_ratio']} | {row['modeled_compute_cost_usd']} |\n"
    text+='\nQuality preserved: '+str(result['quality_preserved'])+'. Modeled dollar reduction: '+str(reduction)+'.\n\n'+steps[0]['cost_basis']
    record_section(root,'BENCHMARKS.md','Local model cache replay',text)
    return result


def local_throughput(root,factory=None):
    root=Path(root);factory=factory or (lambda:configured_client('open_weight'))
    cases=[c for c in json.loads((root/'data/golden.json').read_text()) if c['intent']=='faq']
    client=factory();correct=0
    start=time.perf_counter()
    for case in cases:
        response=CampusApp(client).respond(case['text'])
        correct+=response.get('answer')==case['answer']
    elapsed=time.perf_counter()-start
    completed=[r for r in client.logs if r['status']=='ok']
    result={'workload':'serial FAQ through the actual SDK/model, with warm prefix cache; not saturation capacity',
            'attempted_requests':len(cases),'completed_model_calls':len(completed),'wall_seconds':elapsed,
            'completed_requests_per_second':len(completed)/elapsed,'quality_rate':correct/len(cases),
            'all_model_calls_succeeded':len(completed)==len(cases), 'usage':client.logs}
    write_json(root/'local_throughput.json',result)
    record_section(root,'BENCHMARKS.md','Measured local throughput','```json\n'+json.dumps({k:v for k,v in result.items() if k!='usage'},indent=2)+'\n```')
    return result


def economic_scenarios(throughput,hourly_usd,uncached_api_usd,cached_api_usd):
    if not throughput['all_model_calls_succeeded']:raise ValueError('Failed requests cannot establish usable hosting capacity')
    return {name:break_even(hourly_usd,throughput['completed_requests_per_second'],rate) for name,rate in
            [('uncached API',uncached_api_usd),('cached API',cached_api_usd)]}


def validate_reviewed_labels(rows,candidates):
    expected={c['id']:c for c in candidates}
    if len(rows)!=len(expected) or len({r.get('id') for r in rows})!=len(expected):raise ValueError('Review must contain every candidate exactly once')
    for row in rows:
        if row.get('id') not in expected:raise ValueError('Unknown review candidate')
        source=expected[row['id']]
        if any(row.get(k)!=source[k] for k in ('answer','reference','language')):raise ValueError('Review content changed; use the generated candidate set')
        if type(row.get('supported')) is not bool or row.get('owner_approved') is not True:raise ValueError('Every answer needs an explicit human label and approval')
        if not row.get('reviewer') or not row.get('reviewed_at'):raise ValueError('Human reviewer and date required')
    return rows


def run_reviewed_judge(root,label_path,factory=None):
    root=Path(root);cases=json.loads((root/'data/golden.json').read_text())
    rows=validate_reviewed_labels(json.loads(Path(label_path).read_text()),judge_candidates(cases))
    client=(factory or (lambda:configured_client('open_weight')))()
    result=calibrate_judge(rows,client)
    result['label_file_sha256']=hashlib.sha256(Path(label_path).read_bytes()).hexdigest()
    result['judge_backend']=client.primary.name
    record_calibration(root,result)
    return result


def export_results(root):
    root=Path(root);destination=root/'Riwaq_results.zip'
    files=['EVALUATION_REPORT.md','BENCHMARKS.md','evidence.json','local_model_provenance.json',
           'local_evaluation.json','local_cache.json','local_throughput.json','judge_calibration.json',
           'submission_status.json','model-install.log','model-download.log','model-server.log',
           'data/golden.json','data/baseline.v1.json']
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            path=root/name
            if path.is_file():archive.write(path,name)
    return destination


def submission_status(root):
    root=Path(root)
    local=json.loads((root/'local_evaluation.json').read_text()) if (root/'local_evaluation.json').exists() else None
    judge=json.loads((root/'judge_calibration.json').read_text()) if (root/'judge_calibration.json').exists() else None
    cache=json.loads((root/'local_cache.json').read_text()) if (root/'local_cache.json').exists() else None
    status={
        'local_open_weight_run':bool(local),
        'local_safety_green':local['safety_green'] if local else None,
        'local_regression_gate_allowed':local['gate_against_committed_baseline']['allowed'] if local else None,
        'judge_calibrated':bool(judge and judge.get('qualified')),
        'owner_approval_verified':(root/'verified_owner_approval.json').exists(),
        'cached_tokens_observed':bool(cache and any(row['meter']['provider_cached_ratio'] is not None for row in cache['steps'])),
        'hourly_cost_supplied':bool(cache and cache['steps'][0]['hourly_rate_input_usd'] is not None),
        'commercial_comparison':'not established by a local open-weight run',
        'github_and_peer_review':'must be supplied by the owner; not inferred from local files'}
    write_json(root/'submission_status.json',status)
    record_section(root,'EVALUATION_REPORT.md','Submission evidence status','```json\n'+json.dumps(status,indent=2)+'\n```\nNo score or complete rubric compliance is asserted.')
    return status
