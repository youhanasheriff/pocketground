#!/usr/bin/env python3
"""PocketGround: inspect, run and score fixed-context RAG generation tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'fire-safety-v1'
GROUPS = {'book': 'Document answers', 'scope': 'Domain boundaries',
          'handling': 'Uncertainty and stress', 'knowledge': 'Beyond the document'}
STATUSES = {'correct', 'incorrect_or_incomplete', 'unanswered', 'unverified_detail', 'not_applicable'}

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

def message_hash(messages):
    return digest(json.dumps(messages, sort_keys=True))

def selected_cases(dataset, split):
    return [c for c in dataset['cases'] if split == 'all' or c['split'] == split]

def validate_dataset(dataset):
    cases = dataset['cases']
    ids = [c['id'] for c in cases]
    if not cases or len(ids) != len(set(ids)):
        raise ValueError('Case IDs must be present and unique.')
    for c in cases:
        if c['kind'] not in GROUPS or c['split'] not in ('core', 'supplement'):
            raise ValueError(f"Invalid group or split: {c['id']}")
        if len(c['passages']) != 5 or message_hash(c['messages']) != c['prompt_sha256']:
            raise ValueError(f"Context or prompt hash mismatch: {c['id']}")
        if c['split'] != ('supplement' if c['kind'] == 'knowledge' else 'core'):
            raise ValueError('This release reserves knowledge cases for the supplement.')
    return dataset

def score(dataset, records, reviews):
    """Require exact, complete manual judgments. Never infer quality from keywords."""
    if records['split'] not in ('core', 'supplement', 'all'):
        raise ValueError('Unknown reporting split.')
    run_ids = [r['run'] for r in records['runs']]
    if not run_ids or len(run_ids) != len(set(run_ids)):
        raise ValueError('Measured run IDs must be present and unique.')
    expected = selected_cases(dataset, records['split'])
    by_id = {c['id']: c for c in expected}
    runs = []
    for run in records['runs']:
        rows = run['results']
        if [r['id'] for r in rows] != list(by_id):
            raise ValueError('Incomplete, duplicate or reordered results; cannot score.')
        judgments = reviews['runs'].get(str(run['run']), {})
        counts = {k: {'passed': 0, 'total': 0} for k in GROUPS}
        for r in rows:
            c = by_id[r['id']]
            j = judgments.get(r['id'], {})
            if r.get('error') or not isinstance(r.get('answer', {}).get('content'), str):
                raise ValueError(f"API failure requires rerun, not a scored answer: {r['id']}")
            if r['prompt_sha256'] != c['prompt_sha256'] or j.get('sha256') != digest(r['answer']['content']):
                raise ValueError(f"Stale prompt or answer judgment: {r['id']}")
            if type(j.get('task_success')) is not bool or j.get('factual_status') not in STATUSES:
                raise ValueError(f"Complete the manual judgment for {r['id']}")
            if c['kind'] in ('book', 'knowledge') and j['factual_status'] == 'not_applicable':
                raise ValueError(f"Answerable cases need a factual judgment: {r['id']}")
            if c['kind'] in ('scope', 'handling') and j['factual_status'] != 'not_applicable':
                raise ValueError(f"Use task success for scope/handling: {r['id']}")
            if c['kind'] == 'knowledge' and type(j.get('provenance_pass')) is not bool:
                raise ValueError(f"Review knowledge-source disclosure for {r['id']}")
            if not j['task_success'] and not j.get('note', '').strip():
                raise ValueError(f"Explain failed task: {r['id']}")
            counts[c['kind']]['total'] += 1
            counts[c['kind']]['passed'] += j['task_success']
        core = [c for c in expected if c['split'] == 'core']
        runs.append({'run': run['run'], 'groups': counts,
                     'core_passed': sum(judgments[c['id']]['task_success'] for c in core),
                     'core_total': len(core),
                     'median_api_seconds': statistics.median(r['generation_seconds'] for r in rows),
                     'length_cutoffs': sum(r['finish_reason'] == 'length' for r in rows)})
    if not runs:
        raise ValueError('No measured runs.')
    return {'label': records['label'], 'split': records['split'], 'runs': runs}

def request(base, payload, timeout, key_env):
    url = base.rstrip('/') + ('/chat/completions' if base.rstrip('/').endswith('/v1') else '/v1/chat/completions')
    headers = {'Content-Type': 'application/json'}
    key = os.environ.get(key_env)
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)

def run_benchmark(a, dataset):
    if a.out.exists():
        raise ValueError('Output exists; choose a new filename to preserve previous evidence.')
    cases = selected_cases(dataset, a.split)
    if not cases or not a.model.strip() or a.runs < 1:
        raise ValueError('Supply a model, cases and at least one run.')
    result = {'schema_version': 1, 'suite': dataset['suite'], 'label': a.label,
              'split': a.split, 'model_id': a.model, 'python': platform.python_version(),
              'platform': platform.platform(), 'settings': dataset['request_settings'],
              'measurement': 'Non-streaming HTTP completion wall time; excludes retrieval; includes prompt work and decoding.',
              'runtime_configuration': 'User-managed server; record template/build/backend separately. No automatic runtime or weight attestation.',
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'runs': []}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    # Keep completed calls on interruption. An interrupted file is unscorable.
    def save():
        temp = a.out.with_suffix(a.out.suffix + '.tmp')
        temp.write_text(json.dumps(result, indent=2) + '\n')
        temp.replace(a.out)
    for run_number in range(1, a.runs + 1):
        trial = {'run': run_number, 'results': []}
        result['runs'].append(trial)
        warmup_messages = [{'role': 'system', 'content': dataset['system_prompt']},
                           {'role': 'user', 'content': 'CONTEXT:\n[P1] The test marker is READY.\n\nQUESTION:\nWhat is the test marker?\n\nANSWER:'}]
        trial['warmup'] = request(a.base_url, {'model': a.model, 'messages': warmup_messages, **dataset['request_settings']}, a.timeout, a.api_key_env)
        save()
        for c in cases:
            started = time.perf_counter()
            raw = request(a.base_url, {'model': a.model, 'messages': c['messages'], **dataset['request_settings']}, a.timeout, a.api_key_env)
            seconds = time.perf_counter() - started
            choice = raw['choices'][0]
            if not isinstance(choice.get('message', {}).get('content'), str):
                raise ValueError(f"Server did not return a text answer: {c['id']}")
            trial['results'].append({'id': c['id'], 'answer': choice['message'],
                                     'finish_reason': choice['finish_reason'], 'usage': raw.get('usage', {}),
                                     'timings': raw.get('timings', {}), 'generation_seconds': round(seconds, 6),
                                     'prompt_sha256': c['prompt_sha256']})
            save()
            print(f"Run {run_number} / {c['id']}: {seconds:.3f}s", flush=True)
    result['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    save()
    print(f'Saved {a.out}. Generate a review sheet next; answers are not automatically graded.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DATA / 'dataset.json')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inspect', help='Show the dataset and its question groups.')
    sub.add_parser('verify', help='Verify all pinned release files and reference scores.')
    models = sub.add_parser('models', help='Print pinned downloads and model hashes.')
    models.add_argument('--key')
    run = sub.add_parser('run', help='Run frozen questions against a local chat API.')
    run.add_argument('--base-url', default='http://127.0.0.1:1234/v1')
    run.add_argument('--model', required=True)
    run.add_argument('--label', required=True)
    run.add_argument('--split', choices=['all', 'core', 'supplement'], default='all')
    run.add_argument('--runs', type=int, default=2)
    run.add_argument('--timeout', type=int, default=120)
    run.add_argument('--api-key-env', default='POCKETGROUND_API_KEY')
    run.add_argument('--out', type=Path, required=True)
    review = sub.add_parser('review-sheet', help='Create ungraded, hash-bound manual judgments.')
    review.add_argument('results', type=Path)
    review.add_argument('--out', type=Path, required=True)
    scoring = sub.add_parser('score', help='Score completed manual judgments.')
    scoring.add_argument('results', type=Path)
    scoring.add_argument('review', type=Path)
    a = parser.parse_args()
    if a.command == 'verify':
        from validate import validate_release
        print(json.dumps(validate_release(), indent=2))
        return
    dataset = validate_dataset(read(a.dataset))
    if a.command == 'inspect':
        print(f"{dataset['suite']} — {len(dataset['cases'])} frozen questions")
        for kind, label in GROUPS.items():
            print(f"  {label}: {sum(c['kind'] == kind for c in dataset['cases'])}")
        print(f"Core = {sum(c['split']=='core' for c in dataset['cases'])}. Supplement = {sum(c['split']=='supplement' for c in dataset['cases'])}. Default run preserves frozen order.")
        print('Measured source: one fire-safety booklet. No cross-domain or headset reliability claim.')
    elif a.command == 'models':
        for m in read(ROOT / 'data/models.json'):
            if a.key and m['key'] != a.key:
                continue
            print(f"{m['key']}: {m['name']} ({m['profile']['bytes'] / 1e6:.1f} MB)")
            print(m['download_url'])
            print('SHA256: ' + m['profile']['sha256'])
    elif a.command == 'run':
        run_benchmark(a, dataset)
    elif a.command == 'review-sheet':
        result = read(a.results)
        review = {'instructions': 'Review against dataset expected behaviors and source passages. Null means unreviewed. Explain every failed task. Never judge by keywords alone.', 'runs': {}}
        for trial in result['runs']:
            review['runs'][str(trial['run'])] = {r['id']: {'sha256': digest(r['answer']['content']),
                'task_success': None, 'factual_status': None, 'provenance_pass': None, 'note': ''} for r in trial['results']}
        write_new(a.out, review)
        print(a.out)
    elif a.command == 'score':
        print(json.dumps(score(dataset, read(a.results), read(a.review)), indent=2))

if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.URLError) as error:
        sys.exit(f'PocketGround: {error}')
