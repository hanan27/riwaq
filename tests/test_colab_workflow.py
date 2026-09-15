"""Control-plane tests only: no GPU throughput or model-quality claims."""
import json
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from colab_runtime import server_command,gpu_info
from riwaq import configured_client
from live import judge_candidates
from review import build_review,validate_owner_approval
from local_experiments import validate_reviewed_labels,local_cache_experiment,local_throughput,export_results,submission_status,run_local_evaluation

class ColabWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        for name in ['data','templates']:
            shutil.copytree(ROOT/name,self.root/name)
    def tearDown(self):self.tmp.cleanup()

    def test_server_flags_preserve_strict_local_boundary(self):
        config=json.loads((ROOT/'configs/colab_model.json').read_text())
        cmd=server_command('/python',config,'/snapshot')
        self.assertEqual(cmd[cmd.index('--host')+1],'127.0.0.1')
        for flag in ['--enable-auto-tool-choice','--enable-prefix-caching','--enable-prompt-tokens-details','--no-enable-log-requests','--no-enable-log-outputs']:
            self.assertIn(flag,cmd)
        self.assertEqual(cmd[cmd.index('--tool-call-parser')+1],'hermes')
        self.assertNotIn('--trust-remote-code',cmd)
        config['host']='0.0.0.0'
        with self.assertRaises(ValueError):server_command('/python',config,'/snapshot')

    def test_unsupported_host_fails_before_downloads(self):
        with patch('colab_runtime.platform.system',return_value='Darwin'):
            with self.assertRaisesRegex(RuntimeError,'Colab GPU'):gpu_info()

    def test_review_starts_with_no_human_labels(self):
        page=build_review(self.root).read_text()
        payload=json.loads(page.split('<script id="payload" type="application/json">')[1].split('</script>')[0])
        self.assertEqual(len(payload['candidates']),40)
        self.assertTrue(all(c['supported'] is None and not c['owner_approved'] for c in payload['candidates']))
        self.assertNotIn('fetch(',page)
        cases=json.loads((self.root/'data/golden.json').read_text())
        self.assertEqual(payload['golden_sha256'],hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest())

    def test_human_review_cannot_change_candidate_facts(self):
        cases=json.loads((self.root/'data/golden.json').read_text())
        candidates=judge_candidates(cases)
        # Synthetic fixture for validation only; never calibration evidence.
        rows=[dict(c,supported=True,owner_approved=True,reviewer='test fixture',reviewed_at='test date') for c in candidates]
        self.assertEqual(validate_reviewed_labels(rows,candidates),rows)
        rows[0]['answer']='changed reference facts'
        with self.assertRaisesRegex(ValueError,'changed'):validate_reviewed_labels(rows,candidates)
        with self.assertRaises(ValueError):validate_reviewed_labels(candidates,candidates)

    def test_golden_approval_binds_hash_and_membership(self):
        cases=json.loads((self.root/'data/golden.json').read_text())
        approval={'golden_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest(),
                  'case_ids':[c['id'] for c in cases],'owner_approved':True,'reviewer':'test fixture','reviewed_at':'test date'}
        path=self.root/'test_approval.json';path.write_text(json.dumps(approval))
        self.assertEqual(validate_owner_approval(self.root,path),approval)
        approval['case_ids'].pop();path.write_text(json.dumps(approval))
        with self.assertRaises(ValueError):validate_owner_approval(self.root,path)

    def test_unrun_sections_cannot_appear_complete(self):
        status=submission_status(self.root)
        self.assertFalse(status['local_open_weight_run'])
        self.assertFalse(status['judge_calibrated'])
        self.assertFalse(status['cached_tokens_observed'])
        self.assertFalse(status['hourly_cost_supplied'])

    def test_export_uses_allowlist_and_omits_labels_and_secrets(self):
        import zipfile
        (self.root/'.env').write_text('not a real secret')
        (self.root/'owner_labels.json').write_text('[]')
        (self.root/'local_throughput.json').write_text('{}')
        with zipfile.ZipFile(export_results(self.root)) as z:
            self.assertIn('local_throughput.json',z.namelist())
            self.assertNotIn('owner_labels.json',z.namelist());self.assertNotIn('.env',z.namelist())

    def test_local_orchestration_keeps_unknown_costs_unknown(self):
        # Inject offline factory solely to test orchestration; outputs live only in a temporary test folder.
        result=local_cache_experiment(self.root,factory=configured_client,repeats=2)
        self.assertTrue(result['quality_preserved'])
        self.assertIsNone(result['modeled_cost_reduction'])
        for row in result['steps']:
            self.assertIsNone(row['modeled_compute_cost_usd'])
            self.assertIsNone(row['meter']['provider_cached_ratio'])
        throughput=local_throughput(self.root,factory=configured_client)
        self.assertEqual(throughput['attempted_requests'],20)
        self.assertEqual(throughput['quality_rate'],1)

if __name__=='__main__':unittest.main()
