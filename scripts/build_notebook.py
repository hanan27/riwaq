"""Build a clean notebook that imports the actual GitHub checkout."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
cells = []
def md(s): cells.append(dict(cell_type='markdown', metadata={}, source=s.splitlines(True)))
def code(s): cells.append(dict(cell_type='code', metadata={}, source=s.splitlines(True), outputs=[], execution_count=None))
md('''# Riwaq | رواق
Bilingual fictional campus assistant · Hanan Ahmed Alahmadi

Choose **Runtime → Run all**. Default: no-secret, deterministic simulator through the real application and SDK mock transport. This demonstrates behavior, not model quality. Internet is needed for checkout/dependencies. No GPU is required.
The live conversation appears below the safety checks. Optional Hugging Face model evaluation is disabled by default.
''')
code('''import json, os, sys, subprocess
from pathlib import Path
# Use an existing checkout, or clone the real repository in Colab.
ROOT = Path(os.environ.get('RIWAQ_ROOT', '/content/riwaq' if Path('/content').exists() else '.')).resolve()
if not (ROOT / 'src/riwaq.py').exists():
    subprocess.run(['git', 'clone', 'https://github.com/hanan27/riwaq.git', str(ROOT)], check=True)
assert (ROOT / 'configs/models.json').is_file()
if os.environ.get('RIWAQ_SKIP_INSTALL') != '1':
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements-demo.txt')], check=True)
sys.path.insert(0, str(ROOT / 'src'))
import riwaq
assert Path(riwaq.__file__).resolve() == ROOT / 'src/riwaq.py'
from backends import configuration
config = configuration()
print('Executed checkout:', ROOT)
subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], check=True)
print(json.dumps(config, indent=2))
''')
md('## Deterministic safety checks\nSimulated responses test production code, including the unchanged R079 golden expectation.')
code('''import unittest
suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
checks = unittest.TextTestRunner(verbosity=1).run(suite)
assert checks.wasSuccessful()
from evidence import case_session
from riwaq import CampusApp, Session, configured_client, language
case = next(c for c in json.loads((ROOT / 'data/golden.v1.json').read_text()) if c['id'] == 'R079')
app = CampusApp()
result = app.respond(case['text'], case_session(case))
assert result['status'] == case['expected'] == 'refused' and not app.tools.bookings
print('R079:', result)
''')
md('''## Live bilingual conversation — simulator
These responses are generated now by the deterministic simulator using `CampusApp.respond`.
The fictional student session below grants consent only for Monday 9. It is test identity, not real authentication.
After Run all, enter Arabic or English text and press Send. Booking requires the explicit consent checkbox.
''')
code('''app = CampusApp(cache=True)
for text, session in [('What are the admissions documents?', Session()),
                      ('كم رسوم السجل الأكاديمي؟', Session()),
                      ('Book Monday 9', Session('student-demo', ('student',), 'mon-09')),
                      ('أحتاج موظف', Session())]:
    print('You:', text)
    print('Riwaq:', app.respond(text, session))
import ipywidgets as widgets
from IPython.display import display
message = widgets.Text(placeholder='Ask in Arabic or English', description='Message:')
slot = widgets.Dropdown(options=['mon-09', 'tue-11'], description='Slot:')
consent = widgets.Checkbox(value=False, description='I confirm this booking slot')
send = widgets.Button(description='Send')
conversation = widgets.Output()
def reply(_):
    session = Session('student-demo', ('student',), slot.value if consent.value else None)
    with conversation:
        print('You:', message.value)
        print('Riwaq:', app.respond(message.value, session)['answer'])
    consent.value = False
send.on_click(reply)
display(widgets.VBox([message, slot, consent, send, conversation]))
''')
md('## Production request stages\nThe following cell calls the same five functions used by `respond`. Production prompt text lives only in `prompts/`; metering records prompt versions and hashes.')
code('''stage_app = CampusApp()
text = 'What are the admissions documents?'
safe, layer = stage_app.stage_input(text)
assert safe
intent = stage_app.stage_route(text)
source = stage_app.stage_context(text)
raw = stage_app.stage_execute(text, intent, source, Session())
final = stage_app.stage_output(raw, language(text), source, intent)
print({'input': layer, 'route': intent, 'context': source, 'execute': raw, 'output': final})
print('Prompt evidence:', [{k: r.get(k) for k in ('prompt', 'prompt_sha256')} for r in stage_app.client.logs])
''')
md('''## Optional real Hugging Face evaluation
Set one or both flags below and rerun this cell. Local weights need a model download and preferably a T4 GPU; no token is needed for public weights. Hosted inference needs a private `HF_TOKEN` Colab Secret with notebook access and may incur Hugging Face charges. The existing OpenAI SDK is only the HF-compatible transport; no OpenAI service is used.
Missing hosted credentials produce NOT RUN, without benchmark error rows. Review labels independently before adding reviewer/approval/date to `data/judge-calibration.v1.json`. Unreviewed reference agreement is not human calibration. Failed predictions have no kappa.
''')
code('''RUN_HOSTED = False
RUN_LOCAL_MODEL = False
if RUN_HOSTED or RUN_LOCAL_MODEL:
    if not os.getenv('HF_TOKEN'):
        try:
            from google.colab import userdata
            token = userdata.get('HF_TOKEN')
            if token: os.environ['HF_TOKEN'] = token
        except Exception:
            pass
    if RUN_LOCAL_MODEL:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements.txt')], check=True)
    from evaluate import run
    aliases = tuple(name for name, enabled in [('hosted', RUN_HOSTED), ('open_weight', RUN_LOCAL_MODEL)] if enabled)
    result = run(ROOT, aliases=aliases)
    from IPython.display import Markdown
    display(Markdown((ROOT / 'EVALUATION_REPORT.md').read_text()))
    print('Reports saved in', ROOT, '; pending:', result['pending'])
else:
    print('Real model comparison: NOT RUN. Simulator output is not model evaluation.')
''')
md('''## Before resubmission
Inspect every executed cell. If running real evaluation, download `EVALUATION_REPORT.md` and `run-results.json` from the Colab Files panel under `riwaq`, and inspect failed gates and pending evidence. Save/download the executed notebook. Never paste credentials into cells or commit secrets. Default Run all does not overwrite model reports.
''')
for i, cell in enumerate(cells): cell['id'] = f'riwaq-{i:02d}'
(ROOT / 'Riwaq_Capstone.ipynb').write_text(json.dumps(dict(cells=cells, metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}}, nbformat=4, nbformat_minor=5), ensure_ascii=False, indent=1)+'\n')
print('Built', len(cells), 'cells')
