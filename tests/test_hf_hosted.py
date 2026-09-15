"""HF router contract tests use the real OpenAI SDK with a labelled mock transport."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from backends import configuration, make_client
from riwaq import HTTPClient, FAQAnswer


class HuggingFaceHosted(unittest.TestCase):
    def client(self, handler):
        def adapter(*args, **kwargs):
            return HTTPClient(*args, **kwargs, transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {'HF_TOKEN':'hf_test_only'}, clear=True), patch('backends.HTTPClient',side_effect=adapter):
            return make_client('hosted')

    def response(self, cached=0):
        return httpx.Response(200,json={
            'id':'test-only','object':'chat.completion','created':0,'model':'test-only',
            'choices':[{'index':0,'message':{'role':'assistant','content':'{"answer":"ok","source_id":"test"}'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110,
                     'prompt_tokens_details':{'cached_tokens':cached}}})

    def test_hf_token_router_schema_and_usage_through_sdk(self):
        captured=[]
        def handle(request):
            captured.append(request)
            return self.response()
        client=self.client(handle)
        result=client.complete('faq.v1',{'text':'hello'},256)
        FAQAnswer.model_validate_json(result.text)
        request=captured[0];body=json.loads(request.content)
        self.assertEqual(str(request.url),'https://router.huggingface.co/v1/chat/completions')
        self.assertEqual(request.headers['authorization'],'Bearer hf_test_only')
        self.assertEqual(body['model'],configuration()['hosted']['model'])
        self.assertEqual(body['response_format']['type'],'json_schema')
        self.assertTrue(body['response_format']['json_schema']['strict'])
        row=client.logs[0]
        self.assertEqual(row['input_tokens'],100)
        self.assertEqual(row['output_tokens'],10)
        self.assertGreater(row['latency_ms'],0)
        rates=configuration()['hosted']['prices_usd_per_million']
        self.assertAlmostEqual(row['cost_usd'],(100*rates[0]+10*rates[2])/1e6)
        self.assertNotIn('hf_test_only',json.dumps(client.logs))

    def test_provider_outage_uses_configured_hf_fallback(self):
        models=[]
        def handle(request):
            models.append(json.loads(request.content)['model'])
            return httpx.Response(503,json={'error':{'message':'test outage'}}) if len(models)==1 else self.response()
        client=self.client(handle)
        client.complete('faq.v1',{'text':'hello'},256)
        config=configuration()['hosted']
        self.assertEqual(models,[config['model'],config['fallback_model']])
        self.assertTrue(client.logs[-1]['fallback'])

    def test_unknown_cached_rate_does_not_invent_cost(self):
        client=self.client(lambda request:self.response(cached=20))
        client.complete('faq.v1',{'text':'hello'},256)
        self.assertIsNone(client.logs[0]['cost_usd'])
        self.assertTrue(client.logs[0]['cached_usage_observed'])

    def test_hf_token_required_without_other_credential_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError,'HF_TOKEN'):
                make_client('hosted')

if __name__=='__main__': unittest.main()
