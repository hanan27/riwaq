"""Build the single portable Run All notebook from readable project files."""
import base64
import io
import json
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
    for directory in ('src','data','prompts','configs','eval/rubrics','tests'):
        for p in sorted((ROOT/directory).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts: z.writestr(str(p.relative_to(ROOT)),p.read_bytes())
    z.writestr('requirements.txt',(ROOT/'requirements.txt').read_bytes())
cells=[]
def md(s): cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
def code(s): cells.append({'cell_type':'code','metadata':{},'source':s.splitlines(True),'outputs':[],'execution_count':None})
md('''# Riwaq | رواق
Fictional bilingual campus assistant · Hanan Ahmed Alahmadi

Select a T4 GPU, add `HF_TOKEN` to Colab Secrets, then **Run all**.
The notebook runs hosted Hugging Face inference via the OpenAI SDK and Qwen directly through Transformers on the same frozen golden set.
Hosted API calls use Hugging Face credits/billing. The $1/hour T4 cost is an explicit assumption.

Typed boundary → provider retry/fallback → Pydantic extraction retry/repair → bounded authorized tools → outbound guards.
Versioned prompts and data are embedded from the readable project files. No server is started.
''')
code("""import base64, io, json, os, sys, tempfile, zipfile, subprocess
from pathlib import Path
ROOT=Path(tempfile.mkdtemp(prefix='riwaq-'))
BUNDLE="""+repr(base64.b64encode(buf.getvalue()).decode())+"""
with zipfile.ZipFile(io.BytesIO(base64.b64decode(BUNDLE))) as z:
    z.extractall(ROOT)
subprocess.run([sys.executable,'-m','pip','install','-q','-r',str(ROOT/'requirements.txt')],check=True)
sys.path.insert(0,str(ROOT/'src'))
if not os.getenv('HF_TOKEN'):
    try:
        from google.colab import userdata
        os.environ['HF_TOKEN']=userdata.get('HF_TOKEN')
    except Exception:
        pass
print('Workspace:',ROOT)
print('Private HF token configured:',bool(os.getenv('HF_TOKEN')))
""")
md('''## Configuration and calibration
The hosted model is Qwen3-235B-A22B-Instruct-2507 on DeepInfra, with Novita fallback.
Both routes advertise JSON-schema output and tool support in the Hugging Face catalog.
Provider rates and their source are in the config. Cached-token prices remain unknown.
Review the source-derived labels in `data/judge-calibration.v1.json` independently before setting approval/reviewer/date.
Unreviewed fixture kappa is reported, but never presented as human calibration or used to gate safety.
''')
code("""config=json.loads((ROOT/'configs/models.json').read_text())
print(json.dumps(config,indent=2))
# Edit config here if necessary, keeping model identifiers out of application logic.
(ROOT/'configs/models.json').write_text(json.dumps(config,indent=2))
""")
md('## Deterministic contract and safety tests\nThese tests use explicitly simulated responses. They establish code behavior, not model quality.')
code("""import unittest
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
checks=unittest.TextTestRunner(verbosity=1).run(suite)
assert checks.wasSuccessful(), 'Fix deterministic checks before evaluating models'
""")
md('''## Real evaluation
Both backends run the same versioned cases. Output includes intent/language/difficulty/risk slices,
a fixed-baseline regression gate, cache cost/latency replay, observed provider cache usage,
one-dimension judge agreement, and break-even from measured warmed Qwen throughput.
Missing evidence remains pending; failed gates remain failed.
''')
code("""from evaluate import run
result=run(ROOT)
from IPython.display import Markdown, display
display(Markdown((ROOT/'EVALUATION_REPORT.md').read_text()))
""")
code("""try:
    from google.colab import files
    files.download(str(ROOT/'EVALUATION_REPORT.md'))
    files.download(str(ROOT/'run-results.json'))
except ImportError:
    print('Results saved in',ROOT)
print('Evidence complete:',result['complete'])
print('Regression allowed:',result['regression_allowed'])
""")
md('''## Implementation references
[HF API schema constraints](https://huggingface.co/docs/inference-providers/guides/structured-output) ·
[Qwen Transformers inference](https://qwen.readthedocs.io/en/v2.5/inference/chat.html).
All university policies and student sessions are fictional. Human review is not inferred from generated labels.
''')
(ROOT/'Riwaq_Capstone.ipynb').write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},'nbformat':4,'nbformat_minor':5},ensure_ascii=False,indent=1)+'\n')
print('Built',len(cells),'cells')
