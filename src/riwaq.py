"""Riwaq: original fictional campus assistant. Offline model is a simulator, not weights."""
from __future__ import annotations
import ast
import dataclasses
import difflib
import hashlib
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from privacy import pii_spans, mask_pii, mask_data

# Versioned artifacts are loaded from disk, never defined as inline instruction literals.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = PROJECT_ROOT / 'prompts'
PROMPTS = {path.stem: json.loads(path.read_text()) for path in sorted(PROMPT_DIR.glob('*.json'))}
for artifact in PROMPTS.values():
    if not artifact.get('changelog') or not artifact.get('text'):
        raise ValueError('Every prompt needs a changelog and text')

JUDGE_RUBRIC = (PROJECT_ROOT/'eval/rubrics/groundedness.v1.md').read_text()

def prompt_text(prompt_id):
    text = PROMPTS[prompt_id]['text']
    return text + ('\n\n' + JUDGE_RUBRIC if prompt_id=='judge.v1' else '')

CANARY = 'RIWAQ_INTERNAL_7b31c9'
REFUSAL = {'en': 'I cannot help with that request. Please use the official student support channel.',
           'ar': 'لا أستطيع المساعدة في هذا الطلب. يرجى استخدام قناة دعم الطلاب الرسمية.'}
UNKNOWN = {'en': 'I do not have that information.', 'ar': 'لا تتوفر لدي هذه المعلومة.'}
CATALOG = {
 'transcript': {'id': 'NAM-TR-1', 'en': 'An official transcript costs 25 SAR and takes 2 working days.',
                'ar': 'رسوم السجل الأكاديمي الرسمي 25 ريال ومدة إصداره يومان عمل.'},
 'admissions': {'id': 'NAM-AD-1', 'en': 'Admissions require a school certificate and an identity document.',
                'ar': 'يتطلب القبول شهادة الثانوية ووثيقة الهوية.'},
 'enrolment': {'id': 'NAM-EN-1', 'en': 'Course enrolment opens on 1 September and closes on 10 September.',
               'ar': 'يفتح تسجيل المقررات في 1 سبتمبر ويغلق في 10 سبتمبر.'},
 'advising': {'id': 'NAM-AV-1', 'en': 'Advisor appointments are free. Available slots: Monday 09:00 and Tuesday 11:00.',
              'ar': 'مواعيد المرشد الأكاديمي مجانية. المواعيد المتاحة: الاثنين 09:00 والثلاثاء 11:00.'},
}
CATALOG_VERSION = 'fictional-2026-v1'
SLOTS = {'mon-09', 'tue-11'}

def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = ''.join(' ' if unicodedata.category(c) == 'Cf' else c for c in text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn' and c != '\u0640')
    return re.sub(r'\s+', ' ', text.translate(str.maketrans('أإآى', 'اااي'))).strip()

def language(text):
    return 'ar' if re.search(r'[\u0600-\u06ff]', text) else 'en'

# Guard policy is code, not a prompt. Patterns match normalized data.
ATTACK_PATTERNS = [
 r'(ignore|disregard|override|bypass).{0,50}(instruction|rule|guard|policy|limit|auth)',
 r'(reveal|print|show|leak|expose|give).{0,40}(system prompt|canary|secret|api.?key|password)',
 r'(another|other|someone else).{0,20}(student|person).{0,30}(record|grade|transcript|book)',
 r'(book|access|read|change).{0,30}(another|other|someone else).{0,20}(student|person)',
 r'(تجاهل|تخطي|تجاوز|الغ).{0,40}(تعليمات|قواعد|حمايه|قيود|صلاحيات|تحقق)',
 r'(اكشف|اطبع|اعرض|اظهر|سرب|اعطني).{0,35}(كلمه المرور|كلمة المرور|السر|مفتاح|تعليمات النظام|رمز الكناري)',
 r'(سجل|درجات|بيانات|حجز).{0,30}(طالب اخر|طالبه اخري|شخص اخر)',
 r'(احجز|ادخل|عدل).{0,30}(طالب اخر|شخص اخر)',
 r'(system\s*:|\[system\]|<\|im_start\|>|developer\s*:)',
 r'(نفذ|شغل|execute|run).{0,30}(base64|eval\(|curl|shell|شفرة|شفره)',
 r'(انا المسؤول|انا المدير|i am the admin).{0,60}(اكشف|تجاوز|override|reveal)',
]

def input_guard(text):
    if not isinstance(text, str) or len(text) > 4000:
        return False, 'input_limit'
    variants = [normalize(text), normalize(''.join(c for c in text if unicodedata.category(c) != 'Cf'))]
    for s in variants:
        s = s.translate(str.maketrans({'і': 'i', 'о': 'o', 'е': 'e', 'а': 'a'}))
        if any(re.search(p, s) for p in ATTACK_PATTERNS):
            return False, 'instruction_or_privacy'
        if normalize(CANARY) in s:
            return False, 'canary'
    return True, 'allow'

def output_guard(answer, allowed=None):
    safe, _ = input_guard(answer)
    if not safe or CANARY in answer or pii_spans(answer) or any(artifact['text'] in answer for artifact in PROMPTS.values()):
        return False
    return allowed is None or answer in allowed

def route(text):
    n = normalize(text)
    if re.search(r"(do not|don't|dont|never|cancel).{0,15}(book|reserv)|لا\s+(تحجز|احجز)|الغ.{0,10}حجز", n):
        return 'faq'
    if any(w in n for w in ['human', 'complaint', 'appeal', 'موظف', 'شكوي', 'تظلم']):
        return 'escalation'
    if any(w in n for w in ['book', 'reserve', 'احجز', 'حجز موعد']):
        return 'workflow'
    return 'faq'

def topic(text):
    n = normalize(text)
    for key, words in [('transcript', ['transcript', 'سجل', 'كشف درجات']),
                       ('admissions', ['admission', 'قبول']),
                       ('enrolment', ['enrol', 'enroll', 'تسجيل', 'مقررات']),
                       ('advising', ['advisor', 'advising', 'مرشد', 'ارشاد'])]:
        if any(w in n for w in words):
            return key
    return None

@dataclass(frozen=True)
class Session:
    student_id: str | None = None
    roles: tuple = ()
    confirmed_slot: str | None = None
    def authorize(self, action, slot=None):
        if action == 'book_advisor':
            return bool(self.student_id and 'student' in self.roles and slot in SLOTS and self.confirmed_slot == slot)
        return action in ('lookup_service', 'handoff')

class StrictContract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class AppointmentRequest(StrictContract):
    service: Literal['advising']
    slot: Literal['mon-09', 'tue-11'] | None
    language: Literal['ar', 'en']

    @field_validator('slot', mode='before')
    @classmethod
    def registered_slot(cls, value):
        if value is not None and (not isinstance(value, str) or value not in SLOTS):
            raise ValueError('slot must be a registered appointment slot or null')
        return value

    @classmethod
    def validate(cls, value):
        return cls.model_validate(value)

class FAQAnswer(StrictContract):
    answer: str = Field(min_length=1, max_length=2000)
    source_id: str = Field(min_length=1, max_length=80)

    @field_validator('answer', 'source_id')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('blank values are not allowed')
        return value

class JudgeVerdict(StrictContract):
    supported: bool

class WorkflowAck(StrictContract):
    acknowledged: bool

class LookupArgs(StrictContract):
    topic: Literal['transcript', 'admissions', 'enrolment', 'advising'] | None

class BookingArgs(StrictContract):
    slot: Literal['mon-09', 'tue-11']

class HandoffArgs(StrictContract):
    pass

SCHEMAS = {'faq.v1': FAQAnswer, 'faq.v2-bad': FAQAnswer, 'extract.v1': AppointmentRequest,
           'repair.v1': AppointmentRequest, 'judge.v1': JudgeVerdict, 'workflow.v1': WorkflowAck}

@dataclass
class Reply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    finish_reason: str = 'stop'
    usage_verified: bool = False
    tool_calls: list = field(default_factory=list)
    cached_usage_observed: bool = False

class ModelError(Exception): pass
class RateLimit(ModelError): pass
class Outage(ModelError): pass
class InvalidResponse(ModelError): pass

class LLMClient(Protocol):
    name: str
    def complete(self, prompt_id: str, payload: dict, max_tokens: int, *, messages: list | None = None, tools: list | None = None, tool_choice: str = "auto") -> Reply: ...

# %% ADAPTER SECTION: all network/provider access lives here.
class HTTPClient:
    """The real provider SDK path, also exercised against an explicit offline transport."""
    def __init__(self, name, base_url, model, key='', prices=None, transport=None, simulated=False, request_timeout=15):
        from openai import OpenAI
        import httpx
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
            raise ValueError('Use HTTPS or loopback HTTP for model endpoints')
        self.name, self.model, self.prices, self.simulated = name, model, prices, simulated
        self.cache_identity = (name, base_url, model)
        self.sdk = OpenAI(api_key=key or 'local-no-key', base_url=base_url, max_retries=0,
                          timeout=request_timeout, http_client=httpx.Client(transport=transport, follow_redirects=False))
    def complete(self, prompt_id, payload, max_tokens, *, messages=None, tools=None, tool_choice='auto'):
        from openai import RateLimitError, APIConnectionError, APITimeoutError, APIStatusError
        if not 1 <= max_tokens <= 1024: raise ValueError('output budget')
        # Stable system prefix, then masked per-request payload and bounded conversation tail.
        history = [{'role':'system', 'content':prompt_text(prompt_id)},
                   {'role':'user', 'content':json.dumps(mask_data(payload), ensure_ascii=False)}]
        history += mask_data(messages or [])
        data = {'model':self.model, 'temperature':0, 'max_tokens':max_tokens, 'messages':history}
        if tools and tool_choice != 'none':
            data.update(tools=tools, tool_choice=tool_choice, parallel_tool_calls=False)
        else:
            data['response_format'] = {'type':'json_schema', 'json_schema':{
                'name':SCHEMAS[prompt_id].__name__, 'strict':True, 'schema':SCHEMAS[prompt_id].model_json_schema()}}
        try:
            response = self.sdk.chat.completions.create(**data)
        except RateLimitError: raise RateLimit('provider rate limit') from None
        except (APIConnectionError, APITimeoutError): raise Outage('provider unavailable') from None
        except APIStatusError as exc:
            if exc.status_code >= 500: raise Outage('provider outage') from None
            raise ModelError('provider request rejected') from None
        try:
            choice = response.choices[0]
            usage = response.usage
            details = usage.prompt_tokens_details if usage else None
            raw_cached = getattr(details, 'cached_tokens', None)
            counts = (usage.prompt_tokens, usage.completion_tokens, raw_cached or 0) if usage else (0,0,0)
            if any(type(v) is not int or v < 0 for v in counts) or counts[2] > counts[0]:
                raise InvalidResponse('invalid usage counters')
            return Reply(choice.message.content or '', *counts, choice.finish_reason,
                         usage is not None and not self.simulated,
                         [call.model_dump(exclude_none=True) for call in (choice.message.tool_calls or [])],
                         raw_cached is not None and not self.simulated)
        except (AttributeError, IndexError, TypeError):
            raise InvalidResponse('invalid provider response') from None

class DemoClient:
    """Deterministic simulator. Token counts are estimates; no provider cache or quality claims."""
    def __init__(self, name='offline-simulator', faults=(), responses=()):
        self.name, self.faults, self.responses = name, list(faults), list(responses)
        self.prices = None
    def complete(self, prompt_id, payload, max_tokens, *, messages=None, tools=None, tool_choice='auto'):
        if self.faults:
            fault = self.faults.pop(0)
            if fault: raise fault('scripted fault')
        if self.responses:
            text = self.responses.pop(0)
            if isinstance(text, Reply): return text
        elif prompt_id == 'workflow.v1':
            results = [json.loads(m['content']) for m in (messages or []) if m['role']=='tool']
            if tool_choice == 'none' or any('booking_id' in r or 'error' in r for r in results):
                text = json.dumps({'acknowledged':True})
            else:
                if payload['intent'] == 'escalation': name, args = 'handoff', {}
                elif not results: name, args = 'lookup_service', {'topic':'advising'}
                else: name, args = 'book_advisor', {'slot':payload['request']['slot']}
                return Reply('', 100, 20, finish_reason='tool_calls', tool_calls=[{
                    'id':'call-' + str(len(results)+1), 'type':'function',
                    'function':{'name':name, 'arguments':json.dumps(args)}}])
        elif prompt_id.startswith('faq.'):
            source, lang = payload.get('source'), payload['language']
            answer = source[lang] if source else UNKNOWN[lang]
            if prompt_id == 'faq.v2-bad' and lang == 'ar': answer = answer.replace('25', '250')
            text = json.dumps({'answer': answer, 'source_id': source['id'] if source else 'unknown'}, ensure_ascii=False)
        elif prompt_id in ('extract.v1', 'repair.v1'):
            n = normalize(payload['text'])
            slot = 'mon-09' if any(x in n for x in ['mon-09', 'monday', 'الاثنين']) else 'tue-11' if any(x in n for x in ['tue-11', 'tuesday', 'الثلاثاء']) else None
            text = json.dumps({'service': 'advising', 'slot': slot, 'language': language(payload['text'])})
        elif prompt_id == 'judge.v1':
            text = json.dumps({'supported': normalize(payload['answer']) == normalize(payload['reference'])})
        else: raise ValueError('unknown prompt')
        return Reply(text, math.ceil(len(json.dumps(payload) + PROMPTS[prompt_id]['text']) / 4), math.ceil(len(text) / 4))
def offline_sdk_client():
    import httpx
    config = json.loads((PROJECT_ROOT/'configs/models.json').read_text())['offline']
    simulator = DemoClient()
    def handle(request):
        body = json.loads(request.content)
        prompt_id = next(k for k,v in PROMPTS.items() if prompt_text(k)==body['messages'][0]['content'])
        reply = simulator.complete(prompt_id, json.loads(body['messages'][1]['content']), body['max_tokens'],
                                   messages=body['messages'][2:], tools=body.get('tools'),
                                   tool_choice='auto' if body.get('tools') else 'none')
        message = {'role':'assistant', 'content':reply.text or None}
        if reply.tool_calls: message['tool_calls'] = reply.tool_calls
        return httpx.Response(200,json={'id':'offline-completion','object':'chat.completion','created':0,
            'model':body['model'], 'choices':[{'index':0,'message':message,'finish_reason':reply.finish_reason}],
            'usage':{'prompt_tokens':reply.input_tokens,'completion_tokens':reply.output_tokens,
                     'total_tokens':reply.input_tokens+reply.output_tokens}})
    return HTTPClient('offline-sdk-simulator',config['url'],config['model'],transport=httpx.MockTransport(handle),simulated=True)

# %% END ADAPTER SECTION

class MeteredClient:
    """One boundary for retries, fallback, usage and prompt-version logging."""
    def __init__(self, primary=None, fallback=None, sleep=time.sleep):
        self.primary = primary or offline_sdk_client()
        self.fallback, self.sleep, self.logs = fallback, sleep, []
    def complete(self, prompt_id, payload, max_tokens=256, *, messages=None, tools=None, tool_choice='auto'):
        if prompt_id not in PROMPTS or not 1 <= max_tokens <= 1024: raise ValueError('request budget')
        payload, messages = mask_data(payload), mask_data(messages)
        clients = [self.primary] + ([self.fallback] if self.fallback else [])
        for backend_index, backend in enumerate(clients):
            for attempt in range(2):
                start = time.perf_counter()
                row = {'backend': backend.name, 'prompt': prompt_id, 'attempt': attempt + 1,
                       'fallback': bool(backend_index), 'max_tokens': max_tokens, 'cost_usd':None,
                       'request_id':len(self.logs)+1, 'prompt_sha256':hashlib.sha256(prompt_text(prompt_id).encode()).hexdigest()}
                try:
                    reply = backend.complete(prompt_id, payload, max_tokens, **({'messages':messages,'tools':tools,'tool_choice':tool_choice} if messages is not None or tools is not None else {}))
                    row.update(dataclasses.asdict(reply)); row.pop('text'); row.pop('tool_calls')
                    if not isinstance(reply.text, str) or reply.finish_reason not in ('stop','tool_calls'):
                        raise InvalidResponse('incomplete generation')
                    rates = getattr(backend, 'prices', None)
                    row['cost_usd'] = ((reply.input_tokens - reply.cached_input_tokens) * rates[0] + reply.cached_input_tokens * rates[1] + reply.output_tokens * rates[2]) / 1e6 if rates and reply.usage_verified else None
                    row['status'] = 'ok'
                    return reply
                except (RateLimit, Outage, InvalidResponse) as e:
                    row['status'] = type(e).__name__
                    if isinstance(e, RateLimit) and attempt == 0:
                        self.sleep(min(0.25 * (2 ** attempt), 2.0))
                        continue
                    break
                except ModelError as e:
                    row['status'] = type(e).__name__
                    raise
                finally:
                    row['latency_ms'] = (time.perf_counter() - start) * 1000
                    self.logs.append(row)
        raise Outage('all configured backends exhausted')

def configured_client(name='offline'):
    if name == 'offline': return MeteredClient()
    if name not in ('commercial', 'open_weight'): raise ValueError('unknown backend')
    prefix = 'RIWAQ_' + name.upper()
    base, model = os.getenv(prefix + '_URL'), os.getenv(prefix + '_MODEL')
    if not base or not model: raise ValueError('Set ' + prefix + '_URL and _MODEL')
    rates = [os.getenv(prefix + suffix) for suffix in ('_INPUT_USD_M', '_CACHED_USD_M', '_OUTPUT_USD_M')]
    prices = tuple(float(v) for v in rates) if all(v is not None for v in rates) else None
    fallback_name = os.getenv(prefix + '_FALLBACK')
    fallback = None
    if fallback_name:
        if fallback_name not in ('commercial','open_weight') or fallback_name == name: raise ValueError('invalid fallback alias')
        fp = 'RIWAQ_' + fallback_name.upper()
        fallback = HTTPClient(fallback_name, os.environ[fp+'_URL'], os.environ[fp+'_MODEL'], os.getenv(fp+'_KEY',''))
    timeout = float(os.getenv(prefix + '_TIMEOUT_SECONDS', '15'))
    if not 1 <= timeout <= 120: raise ValueError('Request timeout must be 1–120 seconds')
    return MeteredClient(HTTPClient(name, base, model, os.getenv(prefix + '_KEY', ''), prices, request_timeout=timeout), fallback)

def extract_request(client, text):
    trace = []
    for prompt_id in ('extract.v1', 'extract.v1', 'repair.v1'):
        payload = {'text': text, 'validation_errors': trace}
        try:
            reply = client.complete(prompt_id, payload, 160)
            value = AppointmentRequest.model_validate_json(reply.text)
            trace.append({'stage': prompt_id, 'valid': True})
            return value, trace
        except (ValueError, TypeError) as e:
            errors = e.errors(include_input=False, include_context=False, include_url=False) if isinstance(e, ValidationError) else [{'type':'json_invalid','msg':'Invalid JSON object'}]
            trace.append({'stage':prompt_id, 'valid':False, 'errors':mask_data(errors)})
    return None, trace

TOOL_MODELS = {'lookup_service':LookupArgs, 'book_advisor':BookingArgs, 'handoff':HandoffArgs}
TOOL_DESCRIPTIONS = json.loads((PROJECT_ROOT/'configs/tools.v1.json').read_text())

def tool_definitions(intent):
    names = ('handoff',) if intent=='escalation' else ('lookup_service','book_advisor')
    return [{'type':'function','function':{'name':name,'description':TOOL_DESCRIPTIONS[name],
            'strict':True,'parameters':TOOL_MODELS[name].model_json_schema()}} for name in names]

class Tools:
    RISKS = {'lookup_service': 'read-only', 'book_advisor': 'side-effecting', 'handoff': 'terminal'}
    def __init__(self): self.bookings, self.logs, self.handoffs = {}, [], []
    def call(self, name, args, session, iteration):
        risk = self.RISKS.get(name, 'unknown')
        log = {'tool': name, 'risk': risk, 'iteration': iteration, 'status': 'denied'}
        self.logs.append(log)
        if not 1 <= iteration <= 3: raise PermissionError('loop limit')
        if name not in self.RISKS: raise PermissionError('tool not registered')
        try:
            args = TOOL_MODELS[name].model_validate(args).model_dump()
        except ValidationError:
            raise PermissionError('invalid tool arguments') from None
        if not session.authorize(name, args.get('slot')): raise PermissionError('session authorization required')
        if name == 'lookup_service': result = CATALOG.get(args['topic'])
        elif name == 'book_advisor':
            slot = args['slot']
            if slot not in SLOTS: raise PermissionError('unknown slot')
            owner = self.bookings.get(slot)
            if owner and owner != session.student_id: raise PermissionError('slot unavailable')
            self.bookings[slot] = session.student_id
            result = {'booking_id': 'B-' + hashlib.sha256((session.student_id + slot).encode()).hexdigest()[:8], 'slot': slot}
        else:
            result = {'handoff_id': 'H-' + str(len(self.handoffs) + 1), 'terminal': True}
            self.handoffs.append(result)
        log['status'] = 'ok'
        return result

def semantic_similarity(left, right):
    # Require the same answer-changing topic and language before fuzzy matching.
    if topic(left) is None or topic(left) != topic(right) or language(left) != language(right):
        return 0.0
    return difflib.SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def calibrate_semantic(pairs):
    scored = [(semantic_similarity(p['left'], p['right']), p['same_answer']) for p in pairs]
    candidates = sorted({score for score, _ in scored} | {1.01})
    feasible = [t for t in candidates if all(score < t for score, positive in scored if not positive)]
    threshold = min(feasible)
    return {'threshold': threshold, 'n': len(scored),
            'true_hits': sum(score >= threshold and positive for score, positive in scored),
            'wrong_hits': sum(score >= threshold and not positive for score, positive in scored),
            'scores': [{'score': score, 'same_answer': positive} for score, positive in scored]}


class ResponseCache:
    """Public FAQ only; optional lexical-similarity tier requires an explicit measured threshold."""
    def __init__(self, semantic_threshold=None):
        self.entries, self.semantic_threshold = {}, semantic_threshold
    def key(self, text, lang, source, prompt, backend):
        return (text, lang, json.dumps(source, ensure_ascii=False, sort_keys=True), CATALOG_VERSION, prompt, hashlib.sha256(prompt_text(prompt).encode()).hexdigest(), backend, 'guard.v2-pii')
    def get(self, key):
        if key in self.entries: return self.entries[key]
        if self.semantic_threshold is not None:
            matches = [(semantic_similarity(old[0], key[0]), value) for old, value in self.entries.items() if old[1:] == key[1:]]
            if matches:
                score, value = max(matches, key=lambda item: item[0])
                if score >= self.semantic_threshold: return value
        return None
    def put(self, key, result): self.entries[key] = dict(result)

class CampusApp:
    def __init__(self, client=None, cache=False, faq_prompt='faq.v1', semantic_threshold=None):
        self.client = client or configured_client()
        self.tools, self.cache = Tools(), ResponseCache(semantic_threshold) if cache else None
        self.faq_prompt, self.events = faq_prompt, []
    # Stage 1: input wall
    def stage_input(self, text): return input_guard(text)
    # Stage 2: deterministic router; no hidden model calls
    def stage_route(self, text): return route(text)
    # Stage 3: bounded context, public catalog only
    def stage_context(self, text):
        result = self.tools.call('lookup_service', {'topic': topic(text)}, Session(), 1)
        # Tool data must match the pinned directory; reject injected instructions and changed facts.
        if result != CATALOG.get(topic(text)):
            raise PermissionError('untrusted tool result')
        return result
    # Stage 4: model call or bounded workflow
    def stage_execute(self, text, intent, source, session):
        lang = language(text)
        text = mask_pii(text)
        if intent == 'escalation':
            return self.tool_loop(text, intent, session)
        if intent == 'workflow':
            request, trace = extract_request(self.client, text)
            if request is None or request.slot is None:
                return {'status':'clarify','answer':'حدد الاثنين 9 أو الثلاثاء 11.' if lang=='ar' else 'Choose Monday 9 or Tuesday 11.','extraction':trace}
            return {**self.tool_loop(text,intent,session,request), 'extraction':trace}
        payload = {'text': text, 'language': lang, 'source': source}
        response = FAQAnswer.model_validate_json(self.client.complete(self.faq_prompt, payload, 256).text).model_dump()
        return {'status': 'answered' if source else 'unknown', **response}
    def tool_loop(self, text, intent, session, request=None):
        lang = language(text)
        payload = {'text':mask_pii(text), 'intent':intent, 'request':request.model_dump() if request else None}
        definitions = tool_definitions(intent)
        allowed_names = {t['function']['name'] for t in definitions}
        history, seen_ids = [], set()
        self.tool_transcripts = getattr(self, 'tool_transcripts', [])
        outcome = None
        # At most three tool rounds plus one tool-result acknowledgement; each call is metered.
        for iteration in range(1,5):
            finalizing = outcome is not None or iteration == 4
            try:
                reply = self.client.complete('workflow.v1', payload, 256, messages=history,
                    tools=definitions, tool_choice='none' if finalizing else 'auto')
            except ModelError:
                if outcome is not None: return outcome  # An action already committed must not appear undone.
                raise
            if finalizing:
                # The server's receipt is authoritative even if acknowledgement is invalid.
                if outcome is not None: return outcome
                return {'status':'refused','answer':REFUSAL[lang]}
            if not reply.tool_calls or len(reply.tool_calls) != 1:
                return {'status':'refused','answer':REFUSAL[lang]}
            call = reply.tool_calls[0]
            try:
                call_id, function = call['id'], call['function']
                name = function['name']
                if not isinstance(call_id,str) or not call_id or call_id in seen_ids or len(call_id)>100:
                    raise PermissionError('invalid call identity')
                seen_ids.add(call_id)
                if name not in allowed_names: raise PermissionError('tool not allowed on route')
                args = json.loads(function['arguments'])
                # Fail the entire call before mutation if the model changes the extracted request.
                if name=='book_advisor' and (request is None or not isinstance(args,dict) or args.get('slot')!=request.slot):
                    raise PermissionError('slot changed by model')
                history.append({'role':'assistant','content':None,'tool_calls':mask_data([call])})
                result = self.tools.call(name,args,session,iteration)
                if name=='lookup_service':
                    if result != CATALOG.get(args['topic']) or (result and (not output_guard(result['en']) or not output_guard(result['ar']))):
                        raise PermissionError('poisoned tool result')
                elif name=='book_advisor':
                    outcome = {'status':'booked','answer':('تم الحجز: ' if lang=='ar' else 'Booked: ')+result['slot'], **result}
                elif name=='handoff':
                    outcome = {'status':'handoff','answer':'تم تحويل الطلب للدعم.' if lang=='ar' else 'The request was handed to support.', **result}
                history.append({'role':'tool','tool_call_id':call_id,'content':json.dumps(mask_data(result),ensure_ascii=False)})
                self.tool_transcripts.append({'iteration':iteration,'tool':name,'messages':mask_data(history.copy())})
                if name=='handoff': return outcome  # terminal tool prevents all further model/tool calls
            except (PermissionError, ValueError, TypeError, KeyError):
                # Fixed error avoids echoing untrusted arguments, PII or provider error bodies.
                if history and history[-1]['role']=='assistant':
                    history.append({'role':'tool','tool_call_id':call_id,'content':json.dumps({'error':'not_authorized_or_invalid'})})
                    outcome = {'status':'refused','answer':REFUSAL[lang]}
                    self.tool_transcripts.append({'iteration':iteration,'tool':'denied','messages':mask_data(history.copy())})
                    continue
                return {'status':'refused','answer':REFUSAL[lang]}
        return outcome or {'status':'refused','answer':REFUSAL[lang]}

    # Stage 5: output wall, including indirect-injection and exact grounding checks
    def stage_output(self, result, lang, source=None, intent='faq'):
        allowed = [source[lang] if source else UNKNOWN[lang]] if intent == 'faq' else None
        source_ok = intent != 'faq' or result.get('source_id') == (source['id'] if source else 'unknown')
        if not source_ok or not output_guard(result['answer'], allowed):
            return {'status': 'refused', 'answer': REFUSAL[lang]}
        return result
    def respond(self, text, session=None):
        session = session or Session()
        lang = language(text) if isinstance(text, str) else 'en'
        safe, layer = self.stage_input(text)
        self.events.append({'language': lang, 'allowed': safe, 'layer': layer})
        if not safe: return {'status': 'refused', 'answer': REFUSAL[lang]}
        text = mask_pii(text)
        intent = self.stage_route(text)
        try:
            source = self.stage_context(text) if intent == 'faq' else None
            key = self.cache.key(text, lang, source, self.faq_prompt, getattr(self.client.primary,'cache_identity',self.client.primary.name)) if self.cache and intent == 'faq' else None
            if key:
                cached = self.cache.get(key)
                if cached: return {**self.stage_output(cached, lang, source, intent), 'cache_hit': True}
            result = self.stage_output(self.stage_execute(text, intent, source, session), lang, source, intent)
            if key and result['status'] in ('answered', 'unknown'): self.cache.put(key, result)
            return result
        except PermissionError:
            return {'status': 'refused', 'answer': REFUSAL[lang]}
        except (ModelError, ValueError, TypeError, KeyError):
            return {'status': 'unavailable', 'answer': 'الخدمة غير متاحة الآن. يرجى المحاولة لاحقا.' if lang == 'ar' else 'Service unavailable. Please try again later.'}

def architecture_check(source):
    tree = ast.parse(source)
    start, end = source.index('# %% ADAPTER SECTION'), source.index('# %% END ADAPTER SECTION')
    start_line, end_line = source[:start].count('\n') + 1, source[:end].count('\n') + 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
            if any(n.split('.')[0] in ('openai', 'anthropic', 'urllib', 'requests', 'httpx') for n in names):
                assert start_line <= node.lineno <= end_line, 'provider access outside adapter'
    assert all(v.get('changelog') and v.get('text') for v in PROMPTS.values())
    assert all((PROMPT_DIR/(key+'.json')).is_file() for key in PROMPTS)
    assert issubclass(AppointmentRequest, BaseModel)
    return True
