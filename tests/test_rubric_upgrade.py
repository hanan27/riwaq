import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from riwaq import *
from evidence import run_golden, regression_gate, privacy_report, calibrate_judge
from live import meter_summary


def call(name,args,identifier='one'):
    return Reply('',finish_reason='tool_calls',tool_calls=[{'id':identifier,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}])

class RubricUpgrade(unittest.TestCase):
    def test_offline_pipeline_actually_invokes_sdk(self):
        adapter=offline_sdk_client()
        with patch.object(adapter.sdk.chat.completions,'create',wraps=adapter.sdk.chat.completions.create) as create:
            result=CampusApp(MeteredClient(adapter)).respond('transcript fee')
            self.assertEqual(result['status'],'answered')
            self.assertEqual(create.call_count,1)
            self.assertEqual(create.call_args.kwargs['response_format']['type'],'json_schema')
        self.assertFalse(adapter.complete('faq.v1',{'text':'transcript fee','language':'en','source':CATALOG['transcript']},256).usage_verified)

    def test_schema_validator_errors_return_to_repair_without_pii(self):
        payloads=[]
        class Broken(DemoClient):
            def complete(self,prompt_id,payload,max_tokens,**kwargs):
                payloads.append(payload)
                return super().complete(prompt_id,payload,max_tokens,**kwargs)
        client=MeteredClient(Broken(responses=['{"service":"advising","slot":"bad","language":"en"}','{}','{"service":"advising","slot":"mon-09","language":"en"}']))
        request,trace=extract_request(client,'Book Monday 9; ID 1234567890')
        self.assertEqual(request.slot,'mon-09')
        self.assertEqual(trace[0]['errors'][0]['loc'],('slot',))
        self.assertTrue(payloads[1]['validation_errors'][0]['errors'][0]['msg'])
        self.assertNotIn('1234567890',json.dumps(payloads))
        self.assertFalse(any('input' in e for t in trace for e in t.get('errors',[])))

    def test_tool_results_are_returned_through_sdk(self):
        adapter=offline_sdk_client()
        with patch.object(adapter.sdk.chat.completions,'create',wraps=adapter.sdk.chat.completions.create) as create:
            app=CampusApp(MeteredClient(adapter))
            result=app.respond('Book Monday 9',Session('a',('student',),'mon-09'))
            self.assertEqual(result['status'],'booked')
            requests=[c.kwargs for c in create.call_args_list]
            tools=[r for r in requests if r.get('tools')]
            self.assertTrue(tools)
            self.assertTrue(all(t['function']['strict'] for r in tools for t in r['tools']))
            self.assertTrue(any(m['role']=='tool' and 'booking_id' in m['content'] for r in requests for m in r['messages']))
            self.assertTrue(any(m['role']=='tool' and 'NAM-AV-1' in m['content'] for r in requests for m in r['messages']))

    def test_model_changed_slot_cannot_act(self):
        client=MeteredClient(DemoClient(responses=[call('book_advisor',{'slot':'tue-11'})]))
        app=CampusApp(client)
        result=app.tool_loop('Book Monday 9','workflow',Session('a',('student',),'tue-11'),AppointmentRequest(service='advising',slot='mon-09',language='en'))
        self.assertEqual(result['status'],'refused'); self.assertFalse(app.tools.bookings)

    def test_parallel_tool_calls_rejected_before_any_action(self):
        parallel=call('book_advisor',{'slot':'mon-09'})
        parallel.tool_calls.append(call('handoff',{},'two').tool_calls[0])
        app=CampusApp(MeteredClient(DemoClient(responses=[parallel])))
        result=app.tool_loop('Book Monday 9','workflow',Session('a',('student',),'mon-09'),AppointmentRequest(service='advising',slot='mon-09',language='en'))
        self.assertEqual(result['status'],'refused'); self.assertFalse(app.tools.bookings)

    def test_loop_bound_and_terminal_handoff(self):
        client=MeteredClient(DemoClient(responses=[call('lookup_service',{'topic':'advising'},str(i)) for i in range(8)]))
        app=CampusApp(client)
        result=app.tool_loop('Book Monday 9','workflow',Session(),AppointmentRequest(service='advising',slot='mon-09',language='en'))
        self.assertEqual(result['status'],'refused'); self.assertEqual(len(client.logs),4)
        terminal=CampusApp()
        self.assertEqual(terminal.respond('I need a human')['status'],'handoff')
        self.assertEqual(len(terminal.client.logs),1)

    def test_committed_action_survives_acknowledgement_outage(self):
        class FailingAck(DemoClient):
            def complete(self,prompt_id,payload,max_tokens,**kwargs):
                if kwargs.get('tool_choice')=='none': raise Outage('failed after write')
                return super().complete(prompt_id,payload,max_tokens,**kwargs)
        app=CampusApp(MeteredClient(FailingAck()))
        result=app.respond('Book Monday 9',Session('a',('student',),'mon-09'))
        self.assertEqual(result['status'],'booked'); self.assertEqual(app.tools.bookings,{'mon-09':'a'})

    def test_saudi_pii_suite_and_harmless_numbers(self):
        result=privacy_report(ROOT)
        self.assertEqual(result['passed'],12)
        for text in ['25 SAR','Monday 09:00','13–16 September 2026','رسوم 25 ريال']:
            self.assertEqual(mask_pii(text),text)

    def test_pii_is_masked_at_sdk_wire_and_outbound_wall(self):
        adapter=offline_sdk_client()
        with patch.object(adapter.sdk.chat.completions,'create',wraps=adapter.sdk.chat.completions.create) as create:
            app=CampusApp(MeteredClient(adapter))
            result=app.respond('My phone is 0501234567. transcript fee?')
            self.assertEqual(result['status'],'answered')
            self.assertNotIn('0501234567',json.dumps(create.call_args.kwargs))
        leaked='Call 0501234567 for a transcript'
        client=MeteredClient(DemoClient(responses=[json.dumps({'answer':leaked,'source_id':'NAM-TR-1'})]))
        self.assertEqual(CampusApp(client).respond('transcript fee')['status'],'refused')

    def test_prompt_artifacts_and_judge_rubric_loaded(self):
        self.assertTrue(architecture_check((ROOT/'src/riwaq.py').read_text()))
        for name in PROMPTS:
            self.assertEqual(json.loads((ROOT/'prompts'/f'{name}.json').read_text()),PROMPTS[name])
        self.assertIn('one dimension only',prompt_text('judge.v1'))
        self.assertTrue(issubclass(AppointmentRequest,BaseModel))
        with self.assertRaises(ValidationError): FAQAnswer(answer='   ',source_id='x')

    def test_frozen_baseline_blocks_regression_and_changed_membership(self):
        cases=json.loads((ROOT/'data/golden.json').read_text())
        before=(ROOT/'data/baseline.v1.json').read_bytes()
        clean=run_golden(cases)
        self.assertTrue(regression_gate(ROOT/'data/baseline.v1.json',clean)['allowed'])
        bad=run_golden(cases,prompt='faq.v2-bad')
        self.assertFalse(regression_gate(ROOT/'data/baseline.v1.json',bad)['allowed'])
        clean['case_ids']=clean['case_ids'][:-1]
        self.assertFalse(regression_gate(ROOT/'data/baseline.v1.json',clean)['allowed'])
        self.assertEqual(before,(ROOT/'data/baseline.v1.json').read_bytes())

    def test_judge_cannot_claim_unreviewed_calibration(self):
        with self.assertRaises(ValueError): calibrate_judge([],MeteredClient())

    def test_missing_cached_usage_is_unknown(self):
        summary=meter_summary([{'status':'ok','usage_verified':True,'input_tokens':100,'cached_input_tokens':0,'cached_usage_observed':False,'cost_usd':.1}])
        self.assertIsNone(summary['provider_cached_ratio'])

    def test_cache_key_changes_with_model_and_prompt_content(self):
        cache=ResponseCache()
        a=cache.key('q','en',CATALOG['transcript'],'faq.v1',('provider','url','model-a'))
        b=cache.key('q','en',CATALOG['transcript'],'faq.v1',('provider','url','model-b'))
        self.assertNotEqual(a,b)

if __name__=='__main__': unittest.main()

class AdditionalBoundaries(unittest.TestCase):
    def test_negative_booking_instruction_never_acts(self):
        for text in ['Do not book Monday 9', "Don't reserve Monday 9", 'لا تحجز الاثنين 9']:
            app=CampusApp()
            app.respond(text,Session('a',('student',),'mon-09'))
            self.assertFalse(app.tools.bookings)

    def test_static_prefix_stays_identical_across_requests(self):
        adapter=offline_sdk_client()
        with patch.object(adapter.sdk.chat.completions,'create',wraps=adapter.sdk.chat.completions.create) as create:
            app=CampusApp(MeteredClient(adapter))
            app.respond('transcript fee')
            app.respond('admissions requirements')
            first,second=[call.kwargs['messages'] for call in create.call_args_list]
            self.assertEqual(first[0],second[0])
            self.assertNotEqual(first[1],second[1])

    def test_invalid_usage_fails_closed(self):
        body={'id':'bad','object':'chat.completion','created':0,'model':'test','choices':[{'index':0,'message':{'role':'assistant','content':'{}'},'finish_reason':'stop'}],
              'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12,'prompt_tokens_details':{'cached_tokens':20}}}
        adapter=HTTPClient('test','https://example.invalid/v1','test',transport=httpx.MockTransport(lambda _:httpx.Response(200,json=body)))
        with self.assertRaises(InvalidResponse):adapter.complete('faq.v1',{},256)
