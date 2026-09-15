"""Two model adapters: hosted SDK and in-process Transformers. No server."""
import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from riwaq import (PROJECT_ROOT, HTTPClient, MeteredClient, Reply, InvalidResponse,
                   SCHEMAS, prompt_text, mask_data)


def configuration():
    return json.loads((PROJECT_ROOT/'configs/models.json').read_text())


class QwenClient:
    name = 'open_weight'
    prices = None

    def __init__(self, config):
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from huggingface_hub import HfApi
        revision = HfApi().model_info(config['model'], revision=config['revision']).sha
        self.tokenizer = AutoTokenizer.from_pretrained(config['model'], revision=revision)
        device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
        dtype = torch.float16 if device == 'cuda' else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(config['model'], revision=revision, torch_dtype=dtype).to(device).eval()
        self.limit = config['context_limit']
        self.model_id = config['model']
        self.cache_identity = (self.name, config['model'], revision)
        self.provenance = {'model':config['model'], 'revision':revision, 'engine':'transformers',
                           'version':transformers.__version__, 'torch':torch.__version__, 'device':device,
                           'hardware':torch.cuda.get_device_name() if device=='cuda' else __import__('platform').platform()}

    def complete(self, prompt_id, payload, max_tokens, *, messages=None, tools=None, tool_choice='auto'):
        import torch
        history = [{'role':'system','content':prompt_text(prompt_id)},
                   {'role':'user','content':json.dumps(mask_data(payload),ensure_ascii=False)}]
        history += mask_data(messages or [])
        # HF chat templates expect parsed tool arguments, unlike the SDK wire format.
        for message in history:
            for call in message.get('tool_calls', []):
                if isinstance(call['function']['arguments'], str):
                    call['function']['arguments'] = json.loads(call['function']['arguments'])
        use_tools = bool(tools and tool_choice != 'none')
        if not use_tools:
            history[0]['content'] += '\n' + prompt_text('local-json.v1') + '\n' + json.dumps(SCHEMAS[prompt_id].model_json_schema())
        rendered = self.tokenizer.apply_chat_template(history, tokenize=False, add_generation_prompt=True,
                                                       **({'tools':tools} if use_tools else {}))
        inputs = self.tokenizer(rendered, return_tensors='pt', add_special_tokens=False).to(self.model.device)
        n = inputs.input_ids.shape[1]
        if n + max_tokens > self.limit: raise InvalidResponse('context budget exceeded')
        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False,
                                             pad_token_id=self.tokenizer.eos_token_id)
        tokens = generated[0, n:]
        text = self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
        calls = []
        if use_tools:
            for i, match in enumerate(re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.S)):
                try:
                    call = json.loads(match)
                    calls.append({'id':f'call_{len(messages or [])}_{i}', 'type':'function',
                                  'function':{'name':call['name'], 'arguments':json.dumps(call['arguments'])}})
                except (ValueError, KeyError, TypeError): raise InvalidResponse('invalid tool JSON') from None
        ended = int(tokens[-1]) in ([self.model.generation_config.eos_token_id] if isinstance(self.model.generation_config.eos_token_id,int) else self.model.generation_config.eos_token_id or [])
        finish = ('tool_calls' if calls else 'stop') if ended else 'length'
        return Reply(text, n, len(tokens), finish_reason=finish, usage_verified=True, tool_calls=calls)


@lru_cache(maxsize=1)
def qwen():
    return QwenClient(configuration()['open_weight'])


def make_client(alias):
    if alias == 'open_weight': return MeteredClient(qwen())
    if alias != 'hosted': raise ValueError('unknown model alias')
    config = configuration()['hosted']
    key = os.getenv('HF_TOKEN')
    if not key: raise ValueError('Set HF_TOKEN privately for optional hosted inference')
    def adapter(model, prices):
        if prices is not None and (len(prices)!=3 or any((p is None and i!=1) or (p is not None and (not math.isfinite(p) or p<0)) for i,p in enumerate(prices))):
            raise ValueError('Finite nonnegative input/output prices required; cached price may be unknown')
        return HTTPClient('hosted', config['url'], model, key, prices, request_timeout=120)
    return MeteredClient(adapter(config['model'],config['prices_usd_per_million']),
                         adapter(config['fallback_model'],config['fallback_prices_usd_per_million']))
