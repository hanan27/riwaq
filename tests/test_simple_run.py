"""Regression coverage for direct inference parsing and honest run accounting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from backends import QwenClient
from evaluate import cache_replay, judge_calibration, write_report
from riwaq import MeteredClient, DemoClient, InvalidResponse


class DirectInference(unittest.TestCase):
    def backend(self, output, eos=99):
        class Tensor:
            shape=(1,10)
            input_ids=None
            def __init__(self): self.input_ids=self
            def to(self,device): return self
            def keys(self): return ['input_ids']
            def __getitem__(self,key): return self
        class Generated:
            def __getitem__(self,key): return [1,2,eos]
        tokenizer=SimpleNamespace(eos_token_id=99,
            apply_chat_template=lambda history,**kw: json.dumps(history),
            decode=lambda tokens,**kw: output)
        class Tokenizer:
            eos_token_id=99
            apply_chat_template=staticmethod(tokenizer.apply_chat_template)
            decode=staticmethod(tokenizer.decode)
            def __call__(self,text,**kw):
                self.rendered=text
                return Tensor()
        model=SimpleNamespace(device='cpu',generation_config=SimpleNamespace(eos_token_id=99),
                              generate=lambda **kwargs: Generated())
        client=QwenClient.__new__(QwenClient)
        client.tokenizer=Tokenizer(); client.model=model; client.limit=4096
        return client

    def test_native_tool_output_normalized_and_pii_masked(self):
        from contextlib import nullcontext
        backend=self.backend('<tool_call>{"name":"book_advisor","arguments":{"slot":"mon-09"}}</tool_call>')
        with patch.dict(sys.modules,{'torch':SimpleNamespace(inference_mode=nullcontext)}):
            reply=backend.complete('workflow.v1',{'text':'Book Monday 9 phone 0501234567'},100,
                                   tools=[{'type':'function','function':{'name':'book_advisor'}}])
        self.assertEqual(reply.finish_reason,'tool_calls')
        self.assertEqual(json.loads(reply.tool_calls[0]['function']['arguments']),{'slot':'mon-09'})
        self.assertNotIn('0501234567',backend.tokenizer.rendered)
        self.assertEqual((reply.input_tokens,reply.output_tokens),(10,3))
        self.assertTrue(reply.usage_verified)
        self.assertFalse(reply.cached_usage_observed)

    def test_context_overflow_fails_before_generation(self):
        backend=self.backend('{}');backend.limit=20
        with patch.dict(sys.modules,{'torch':SimpleNamespace()}):
            with self.assertRaises(InvalidResponse): backend.complete('faq.v1',{},100)

    def test_cache_replay_keeps_measured_request_count_and_quality(self):
        cases=json.loads((ROOT/'data/golden.v1.json').read_text())
        rows=cache_replay(lambda:MeteredClient(DemoClient()),cases)
        self.assertEqual(rows[0]['requests'],2*sum(c['intent']=='faq' for c in cases))
        self.assertEqual(rows[0]['quality'],rows[1]['quality'])
        self.assertLess(rows[1]['meter']['attempts'],rows[0]['meter']['attempts'])
        self.assertIsNone(rows[0]['meter']['cost_usd'])

    def test_unreviewed_fixture_kappa_is_not_human_calibration(self):
        result=judge_calibration(ROOT,lambda:MeteredClient(DemoClient()))
        self.assertFalse(result['human_reviewed'])
        self.assertFalse(result['qualified'])
        self.assertIsInstance(result['kappa'],float)

if __name__=='__main__': unittest.main()
