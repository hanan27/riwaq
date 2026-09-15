"""Safety and evidence regressions; all inference here is simulated."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from riwaq import CampusApp, configured_client, MeteredClient, DemoClient, ModelError
from evidence import case_session, cohen_kappa
from evaluate import judge_calibration, run
from backends import configuration


class Resubmission(unittest.TestCase):
    def test_r079_actual_sdk_application_rejects_without_mutation(self):
        case = next(c for c in json.loads((ROOT/'data/golden.v1.json').read_text()) if c['id']=='R079')
        app = CampusApp(configured_client())
        result = app.respond(case['text'], case_session(case))
        self.assertEqual(case['expected'], 'refused')
        self.assertEqual(result['status'], case['expected'])
        self.assertEqual(app.tools.bookings, {})
        self.assertTrue(app.client.logs)
        self.assertTrue(any(t['tool']=='denied' for t in app.tool_transcripts))

    def test_failed_and_partial_judge_predictions_are_not_calibration(self):
        class Failed(DemoClient):
            def complete(self, *args, **kwargs): raise ModelError('simulated failure')
        for client in (Failed(), DemoClient(faults=[ModelError])):
            result = judge_calibration(ROOT, lambda: MeteredClient(client))
            self.assertEqual(result['status'], 'NOT COMPLETED')
            self.assertIsNone(result['kappa'])
            self.assertIsNone(result['agreement'])
            self.assertFalse(result['qualified'])
        self.assertIsNone(cohen_kappa([True, False], [None, None]))
        self.assertEqual(cohen_kappa([True, False], [True, False]), 1)

    def test_missing_hosted_token_skips_factory_and_benchmarks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('data', 'prompts'):
                (root/name).symlink_to(ROOT/name, target_is_directory=True)
            with patch.dict(os.environ, {}, clear=True), patch('evaluate.configured_client') as factory:
                result = run(root, aliases=('hosted',))
            factory.assert_not_called()
            self.assertEqual(result['backends'], {})
            self.assertIsNone(result['judge']['kappa'])
            self.assertTrue(any('NOT RUN' in s for s in result['pending']))
            self.assertFalse(result['complete'])

    def test_config_is_read_at_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'configs').mkdir()
            path = root/'configs/models.json'
            with patch('backends.PROJECT_ROOT', root):
                for model in ('first-test-model', 'second-test-model'):
                    path.write_text(json.dumps({'hosted': {'model': model}}))
                    self.assertEqual(configuration()['hosted']['model'], model)

    def test_notebook_uses_checkout_and_has_clean_outputs(self):
        notebook = json.loads((ROOT/'Riwaq_Capstone.ipynb').read_text())
        source = '\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code')
        for forbidden in ('b64decode', 'BUNDLE', 'openai/gpt-oss-20b', 'Qwen/Qwen'):
            self.assertNotIn(forbidden, source)
        self.assertIn('configuration()', source)
        self.assertIn('riwaq.__file__', source)
        for cell in notebook['cells']:
            if cell['cell_type']=='code': compile(''.join(cell['source']), '<cell>', 'exec')
