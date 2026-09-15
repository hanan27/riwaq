"""Execute the notebook with its pinned dependencies in a fresh process, capturing real stdout and failures."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import traceback
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'Riwaq_Capstone.ipynb'
notebook=json.loads(path.read_text())
namespace={'__name__':'__main__'}
count=0
with tempfile.TemporaryDirectory(prefix='riwaq-fresh-') as cwd:
    os.chdir(cwd)
    for cell in notebook['cells']:
        if cell['cell_type']!='code': continue
        count+=1
        output=io.StringIO()
        cell['execution_count']=count
        try:
            with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
                exec(compile(''.join(cell['source']),'<notebook-cell-%d>'%count,'exec'),namespace)
        except Exception:
            cell['outputs']=[{'output_type':'stream','name':'stdout','text':output.getvalue().splitlines(True)},
                             {'output_type':'error','ename':'ExecutionError','evalue':'Fresh execution failed','traceback':traceback.format_exc().splitlines()}]
            path.write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n')
            raise
        cell['outputs']=[{'output_type':'stream','name':'stdout','text':output.getvalue().splitlines(True)}] if output.getvalue() else []
        print('Executed cell',count)
path.write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n')
print('PASS:',count,'code cells, fresh working directory, captured actual outputs.')
