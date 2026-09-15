"""Contract and boundary regressions beyond the development golden corpus. No network needed."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from riwaq import *

class Contracts(unittest.TestCase):
    def test_http_wire_contract_and_verified_usage(self):
        data={'id':'contract','object':'chat.completion','created':0,'model':'contract-model',
              'choices':[{'index':0,'message':{'role':'assistant','content':'{"answer":"ok","source_id":"x"}'},'finish_reason':'stop'}],
              'usage':{'prompt_tokens':100,'completion_tokens':12,'total_tokens':112,'prompt_tokens_details':{'cached_tokens':70}}}
        captured={}
        def handle(request):
            captured.update(body=json.loads(request.content),url=str(request.url))
            return httpx.Response(200,json=data)
        adapter=HTTPClient('test-live','https://example.invalid/v1','contract-model',prices=(2,1,4),transport=httpx.MockTransport(handle))
        client=MeteredClient(adapter)
        reply=client.complete('faq.v1',{'text':'hello'},256)
        self.assertEqual(captured['body']['max_tokens'],256)
        self.assertEqual(captured['body']['model'],'contract-model')
        self.assertEqual(captured['url'],'https://example.invalid/v1/chat/completions')
        schema=captured['body']['response_format']
        self.assertEqual(schema['type'],'json_schema')
        self.assertTrue(schema['json_schema']['strict'])
        self.assertFalse(schema['json_schema']['schema']['additionalProperties'])
        self.assertEqual(reply.cached_input_tokens,70)
        self.assertTrue(reply.cached_usage_observed)
        self.assertTrue(reply.usage_verified)
        self.assertAlmostEqual(client.logs[0]['cost_usd'],(30*2+70+12*4)/1e6)

    def test_http_rate_limit_is_retried_and_logged(self):
        def handle(request): return httpx.Response(429,json={'error':{'message':'limited','type':'rate_limit'}})
        adapter=HTTPClient('contract','https://example.invalid/v1','test',transport=httpx.MockTransport(handle))
        delays=[]
        client=MeteredClient(adapter,DemoClient(),sleep=delays.append)
        self.assertEqual(CampusApp(client).respond('transcript fee')['status'],'answered')
        self.assertEqual([r['status'] for r in client.logs],['RateLimit','RateLimit','ok'])
        self.assertEqual(delays,[.25])

    def test_authentication_error_does_not_fallback(self):
        class BadAuth:
            name='auth-failure'
            def complete(self,*args): raise ModelError('HTTP 401')
        client=MeteredClient(BadAuth(),DemoClient())
        result=CampusApp(client).respond('transcript fee')
        self.assertEqual(result['status'],'unavailable')
        self.assertEqual(len(client.logs),1)

    def test_truncated_generation_cannot_be_served(self):
        class Truncated:
            name='truncated'
            def complete(self,*args): return Reply('{"answer":',finish_reason='length')
        client=MeteredClient(Truncated())
        self.assertEqual(CampusApp(client).respond('transcript fee')['status'],'unavailable')
        self.assertEqual(client.logs[0]['status'],'InvalidResponse')

    def test_request_fields_are_not_coerced(self):
        for value in [{'service':'advising','slot':9,'language':'en'},
                      {'service':'advising','slot':'mon-09','language':'english'},
                      {'service':'advising','slot':'mon-09','language':'en','student_id':'victim'}]:
            with self.assertRaises(ValueError): AppointmentRequest.validate(value)

    def test_changed_source_invalidates_warm_cache(self):
        app=CampusApp(cache=True)
        old=app.respond('transcript fee')['answer']
        original=CATALOG['transcript']['en']
        try:
            CATALOG['transcript']['en']='An official transcript costs 30 SAR and takes 2 working days.'
            result=app.respond('transcript fee')
            self.assertNotEqual(result['answer'],old)
            self.assertFalse(result.get('cache_hit',False))
        finally: CATALOG['transcript']['en']=original

    def test_action_replay_never_uses_response_cache(self):
        app=CampusApp(cache=True)
        first=app.respond('Book Monday 9',Session('a',('student',),'mon-09'))
        second=app.respond('Book Monday 9',Session('b',('student',),'mon-09'))
        self.assertEqual(first['status'],'booked')
        self.assertEqual(second['status'],'refused')
        self.assertEqual(app.tools.bookings,{'mon-09':'a'})

    def test_unknown_source_and_incomplete_schema_fail_closed(self):
        for response in ['[]','{"answer": "hello"}','{"answer":"hello","source_id":"wrong"}']:
            app=CampusApp(MeteredClient(DemoClient(responses=[response])))
            self.assertIn(app.respond('transcript fee')['status'],('refused','unavailable'))

if __name__=='__main__': unittest.main()
