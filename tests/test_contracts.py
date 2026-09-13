"""Contract and boundary regressions beyond the development golden corpus. No network needed."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from riwaq import *

class Contracts(unittest.TestCase):
    def test_http_wire_contract_and_verified_usage(self):
        data={'choices':[{'message':{'content':'{"answer":"ok","source_id":"x"}'},'finish_reason':'stop'}],
              'usage':{'prompt_tokens':100,'completion_tokens':12,'prompt_tokens_details':{'cached_tokens':70}}}
        captured={}
        class Opener:
            def open(self,request,timeout):
                captured.update({'body':json.loads(request.data),'timeout':timeout,'url':request.full_url})
                return io.BytesIO(json.dumps(data).encode())
        with patch('urllib.request.build_opener',return_value=Opener()):
            client=MeteredClient(HTTPClient('test-live','https://example.invalid/v1','contract-model',prices=(2,1,4)))
            reply=client.complete('faq.v1',{'text':'hello'},256)
        self.assertEqual(captured['body']['max_tokens'],256)
        self.assertEqual(captured['body']['model'],'contract-model')
        self.assertEqual(captured['url'],'https://example.invalid/v1/chat/completions')
        self.assertEqual(captured['timeout'],15)
        self.assertEqual(reply.cached_input_tokens,70)
        self.assertTrue(reply.usage_verified)
        self.assertAlmostEqual(client.logs[0]['cost_usd'],(30*2+70+12*4)/1e6)

    def test_http_rate_limit_is_retried_and_logged(self):
        adapter=HTTPClient('contract','https://example.invalid/v1','test')
        error=urllib.error.HTTPError('https://example.invalid',429,'rate limited',{},None)
        class Opener:
            def open(self,*args,**kwargs): raise error
        with patch('urllib.request.build_opener',return_value=Opener()):
            client=MeteredClient(adapter,DemoClient(),sleep=lambda _:None)
            self.assertEqual(CampusApp(client).respond('transcript fee')['status'],'answered')
        self.assertEqual([r['status'] for r in client.logs],['RateLimit','RateLimit','ok'])

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
