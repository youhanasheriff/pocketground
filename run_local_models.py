"""Run pinned local configurations in a separate, owned inference process."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import platform
import subprocess
import sys
import time
import urllib.request

from pocketground import DATA, ROOT, read, run_benchmark

def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(8*1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',type=Path,required=True)
    parser.add_argument('--models-root',type=Path,default=Path.home()/'.lmstudio/models')
    parser.add_argument('--keys',nargs='+',default=['q4_current','lfm3_text','lfm3_omni'])
    parser.add_argument('--port',type=int,default=1235)
    parser.add_argument('--output-root',type=Path,default=ROOT/'runs/local-comparison')
    parser.add_argument('--cohort-id',default='local-comparison')
    parser.add_argument('--hardware',default=platform.machine())
    parser.add_argument('--memory-gb',type=float)
    parser.add_argument('--backend',default='unverified; record the actual accelerator/backend')
    args=parser.parse_args()
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',args.port))==0:
            raise ValueError('Benchmark port is occupied; choose another port. No existing service was stopped.')
    registry={m['key']:m for m in read(ROOT/'data/models.json')}
    version=subprocess.run([str(args.server),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if not version:
        version=subprocess.run([str(args.server),'--version'],capture_output=True,text=True,check=True).stderr.strip()
    server_sha=file_sha256(args.server)
    dataset=read(DATA/'dataset.json')
    logs=ROOT/'.runtime';logs.mkdir(exist_ok=True)
    destination=args.output_root
    destination.mkdir(parents=True,exist_ok=True)
    protocol={'id':args.cohort_id,'started_utc':datetime.now(timezone.utc).isoformat(),
        'order':args.keys,'runtime_version':version,'runtime_binary_sha256':server_sha,
        'hardware':{'description':args.hardware,'memory_gb':args.memory_gb,'backend':args.backend},
        'conditions':'Separate sequential benchmark server; existing application servers were left running. No cold-start, peak-RAM or device measurements.',
        'settings':{'context_tokens':4096,'threads':4,'parallel':1,'gpu_layers':99,'temperature':0,
                    'top_k':20,'top_p':.95,'min_p':0,'repeat_penalty':1,'max_answer_tokens':192,
                    'reasoning':'off','tools':False,'multimodal_projector_loaded':False},
        'prompt_hashes':{c['id']:c['prompt_sha256'] for c in dataset['cases']},
        'scope':'Text inputs and text outputs only. Omni speech/vision paths, projector weights, and audio codec were not loaded or evaluated.',
        'comparability':'Use the refreshed Qwen baseline for within-cohort timing comparisons. Original runtime results remain a separate cohort.'}
    protocol_path=destination/'protocol.json'
    protocol_path.parent.mkdir(exist_ok=True)
    if protocol_path.exists():raise ValueError('Cohort protocol already exists; preserve it and choose a new run identity.')
    for key in args.keys:
        model=registry[key];p=model['profile'];weights=args.models_root/p['repository']/p['filename'];out=destination/f'{key}.json'
        if out.exists():raise ValueError(f'Results already exist: {key}')
        if weights.stat().st_size!=p['bytes'] or file_sha256(weights)!=p['sha256']:
            raise ValueError('Pinned model weights failed verification.')
    protocol_path.write_text(json.dumps(protocol,indent=2)+'\n')
    for key in args.keys:
        model=registry[key];p=model['profile'];weights=args.models_root/p['repository']/p['filename'];out=destination/f'{key}.json'
        command=[str(args.server),'--model',str(weights),'--alias','pocketground-candidate','--host','127.0.0.1',
            '--port',str(args.port),'--ctx-size','4096','--parallel','1','--threads','4','--n-gpu-layers','99',
            '--jinja','--reasoning','off','--chat-template-file',str(ROOT/'templates'/p['chat_template']),
            '--no-mmproj','--temp','0','--top-k','20','--top-p','0.95','--min-p','0','--repeat-penalty','1','--predict','192']
        process=None
        with (logs/f'{key}-server.log').open('w') as log:
            try:
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
                for attempt in range(120):
                    if process.poll() is not None:raise RuntimeError(f'{key} server exited; see the private runtime log.')
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/health',timeout=.5) as response:
                            if response.status==200:break
                    except Exception:time.sleep(.25)
                else:raise RuntimeError('Server startup timeout.')
                with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/props',timeout=10) as response:props=json.load(response)
                if Path(props['model_path'])!=weights:raise ValueError('Server loaded an unexpected model.')
                generation=props['default_generation_settings']
                if generation['n_ctx']!=4096:raise ValueError('Unexpected runtime context size.')
                print(f'Running {key}: verified model and 4096-token context.',flush=True)
                run_args=argparse.Namespace(out=out,split='all',model='pocketground-candidate',label=model['name'],runs=2,
                    base_url=f'http://127.0.0.1:{args.port}/v1',timeout=120,api_key_env='POCKETGROUND_BENCHMARK_NO_KEY')
                run_benchmark(run_args,dataset)
                record=read(out)
                record.update(key=key,name=model['name'],profile=p,build=version,cohort=protocol['id'],
                    settings=protocol['settings'],runtime_binary_sha256=server_sha,
                    template_sha256=hashlib.sha256((ROOT/'templates'/p['chat_template']).read_bytes()).hexdigest(),
                    verified_loaded_weight_sha256=p['sha256'])
                out.write_text(json.dumps(record,indent=2)+'\n')
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=15)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
    protocol['completed_utc']=datetime.now(timezone.utc).isoformat()
    protocol_path.write_text(json.dumps(protocol,indent=2)+'\n')

if __name__=='__main__':main()
