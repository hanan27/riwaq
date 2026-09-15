"""Provision an isolated, loopback-only Hugging Face/vLLM server on a Colab GPU.
No inference is simulated here. Linux/NVIDIA are required; unsupported hosts fail clearly.
"""
import atexit
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError


def in_colab():
    return 'google.colab' in sys.modules or bool(os.getenv('COLAB_RELEASE_TAG'))


def gpu_info():
    if platform.system() != 'Linux' or not shutil.which('nvidia-smi'):
        raise RuntimeError('Real-model run requires a Colab GPU. Choose Runtime > Change runtime type > T4 GPU, then Run all.')
    result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],
                          capture_output=True,text=True,check=True,timeout=15)
    return result.stdout.strip()


def server_command(python, config, model_path, prefix_cache=True):
    if config['host']!='127.0.0.1': raise ValueError('Local model must bind only to loopback')
    return [str(python),'-m','vllm.entrypoints.openai.api_server',
        '--model',str(model_path),'--served-model-name',config['served_alias'],
        '--host',config['host'],'--port',str(config['port']),
        '--dtype',config['dtype'],'--max-model-len',str(config['max_model_len']),
        '--max-num-seqs',str(config['max_num_seqs']),
        '--gpu-memory-utilization',str(config['gpu_memory_utilization']),
        '--enforce-eager','--enable-auto-tool-choice','--tool-call-parser',config['tool_call_parser'],
        '--enable-prefix-caching' if prefix_cache else '--no-enable-prefix-caching',
        '--enable-prompt-tokens-details','--no-enable-log-requests','--no-enable-log-outputs',
        '--generation-config','vllm']


def run_logged(command, log_path, label, timeout=1800):
    print(label,flush=True)
    started=time.monotonic()
    with Path(log_path).open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                if time.monotonic()-started>timeout: raise TimeoutError(label+' timed out; inspect '+str(log_path))
                time.sleep(5)
                if int(time.monotonic()-started)%30<5: print(label+' — still working',flush=True)
            if process.returncode: raise RuntimeError(label+' failed; inspect '+str(log_path))
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait()


@dataclass
class LocalServer:
    process: object
    config: dict
    model_path: str
    revision: str
    gpu: str
    log_path: Path
    started_seconds: float

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=20)
            except subprocess.TimeoutExpired: self.process.kill();self.process.wait()

    def provenance(self):
        return {'backend':'open_weight','model_id':self.config['model_id'],'served_alias':self.config['served_alias'],
                'resolved_revision':self.revision,'engine':'vllm','engine_version':self.config['vllm_version'],
                'gpu':self.gpu,'dtype':self.config['dtype'],'context_limit':self.config['max_model_len'],
                'prefix_cache_enabled':True,'model_loading_seconds':self.started_seconds,
                'source':'actual local inference server; no commercial model or price is implied'}


def start_local_model(root):
    root=Path(root)
    config=json.loads((root/'configs/colab_model.json').read_text())
    gpu=gpu_info()  # fail before downloading gigabytes on an unsupported host
    print('GPU:',gpu,flush=True)
    environment=root/'local-model-env'
    python=environment/'bin/python'
    if not python.exists(): subprocess.run([sys.executable,'-m','venv',str(environment)],check=True)
    marker=environment/'installed-version.txt'
    if not marker.exists() or marker.read_text()!=config['vllm_version']:
        run_logged([str(python),'-m','pip','install','vllm=='+config['vllm_version']],root/'model-install.log','Installing isolated model runtime')
        marker.write_text(config['vllm_version'])
    # Run hub download inside the isolated environment. No access token is required for this public repo.
    snapshot_script="""import json,sys
from huggingface_hub import snapshot_download,HfApi
model,revision,destination=sys.argv[1:]
resolved=HfApi().model_info(model,revision=revision).sha
path=snapshot_download(model,revision=resolved,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.jinja','LICENSE*'])
open(destination,'w').write(json.dumps({'path':path,'revision':resolved}))
"""
    info_path=root/'model_snapshot.json'
    run_logged([str(python),'-c',snapshot_script,config['model_id'],config['revision'],str(info_path)],root/'model-download.log','Downloading public Hugging Face model')
    snapshot=json.loads(info_path.read_text())
    # Never assume that an unrelated process on the requested port is our model.
    import socket
    with socket.socket() as probe:
        try: probe.bind((config['host'],config['port']))
        except OSError: raise RuntimeError('Model port is occupied. Stop the earlier RIWAQ_SERVER or restart the runtime.') from None
    log_path=root/'model-server.log'
    started=time.monotonic()
    env=os.environ.copy()
    env.update(VLLM_LOGGING_LEVEL='INFO',TOKENIZERS_PARALLELISM='false',HF_HUB_DISABLE_TELEMETRY='1')
    with log_path.open('w') as log:
        process=subprocess.Popen(server_command(python,config,snapshot['path']),stdout=log,stderr=subprocess.STDOUT,env=env)
    server=LocalServer(process,config,snapshot['path'],snapshot['revision'],gpu,log_path,0)
    atexit.register(server.stop)
    last_progress=0
    try:
        while time.monotonic()-started<config['startup_timeout_seconds']:
            if process.poll() is not None: raise RuntimeError('Model startup failed; inspect '+str(log_path))
            try:
                with urlopen(f"http://{config['host']}:{config['port']}/v1/models",timeout=3) as response:
                    models=json.load(response)
                if config['served_alias'] in {m['id'] for m in models['data']}:
                    server.started_seconds=time.monotonic()-started
                    os.environ['RIWAQ_OPEN_WEIGHT_URL']=f"http://{config['host']}:{config['port']}/v1"
                    os.environ['RIWAQ_OPEN_WEIGHT_MODEL']=config['served_alias']
                    os.environ['RIWAQ_OPEN_WEIGHT_KEY']=''
                    os.environ['RIWAQ_OPEN_WEIGHT_TIMEOUT_SECONDS']='90'
                    # Clear inherited commercial-style token prices: local hardware has a different basis.
                    for suffix in ('_INPUT_USD_M','_CACHED_USD_M','_OUTPUT_USD_M','_FALLBACK'):
                        os.environ.pop('RIWAQ_OPEN_WEIGHT'+suffix,None)
                    (root/'local_model_provenance.json').write_text(json.dumps(server.provenance(),indent=2)+'\n')
                    print('Real open-weight model ready; SDK connects to localhost.',flush=True)
                    return server
            except (URLError,TimeoutError,KeyError,ValueError): pass
            elapsed=time.monotonic()-started
            if elapsed-last_progress>=15:
                print('Loading weights and CUDA kernels —',round(elapsed),'seconds',flush=True);last_progress=elapsed
            time.sleep(2)
        raise TimeoutError('Model startup timed out; inspect '+str(log_path))
    except BaseException:
        server.stop()
        raise
