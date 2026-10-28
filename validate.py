"""Verify evidence integrity and independently reconcile the public scorecard."""
from collections import Counter
import csv
import hashlib
import json
import re
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent

def validate_release():
    def read(p):return json.loads((ROOT/p).read_text())
    manifest=read('manifest.json')
    for path,expected in manifest['sha256'].items():
        target=ROOT/path
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Release checksum mismatch: {path}')
    for path,expected in read('data/original-snapshot.json')['unchanged_files'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,f'Original evidence changed: {path}'
    data=read('data/fire-safety-v1/dataset.json');summary=read('results/scorecard.json')
    cases=data['cases'];ids=[c['id'] for c in cases]
    assert len(ids)==len(set(ids))==40
    assert Counter(c['split'] for c in cases)=={'core':32,'supplement':8}
    assert Counter(c['kind'] for c in cases)=={'book':20,'knowledge':8,'scope':8,'handling':4}
    protocol=read('data/fire-safety-v1/protocol.json')
    for c in cases:
        assert hashlib.sha256(json.dumps(c['messages'],sort_keys=True).encode()).hexdigest()==c['prompt_sha256']==protocol['prompt_hashes'][c['id']]
        assert len(c['passages'])==5
        if c['kind']=='book':assert set(c['expected_pages'])&{p['pdf_page'] for p in c['passages']}
        if c.get('mutation'):
            assert c['passages'][:4]==c['natural_passages'][:4]
            assert c['passages'][4]['synthetic'] and c['passages'][4]['pdf_page'] is None
    count=0;cutoffs=0;original_cutoffs=0;core_scores={}
    expected_core={'q4':28,'q8':28,'qwen2':29,'lfmrag':25,'lfminstruct':23,'minicpm':10}
    for m in summary['models']:
        key=m['key'];raw=read(f'results/reference/{key}.json');review=read(f'results/reference/{key}.review.json')
        assert m['budget_eligible']==(m['bytes']<1_000_000_000)
        assert len(raw['runs'])==2
        for run,derived in zip(raw['runs'],m['runs']):
            assert [r['id'] for r in run['results']]==ids
            jud=review['runs'][str(run['run'])]
            for c,r in zip(cases,run['results']):
                assert hashlib.sha256(r['answer']['content'].encode()).hexdigest()==jud[c['id']]['sha256']
                assert r['prompt_sha256']==c['prompt_sha256']
                assert r['usage']['prompt_tokens']+192<=4096
                assert r['generation_seconds']>=0
                count+=1;cutoffs+=r['finish_reason']=='length'
            n=sum(jud[c['id']]['task_success'] for c in cases if c['split']=='core')
            assert n==derived['core_passed'] and derived['core_total']==32
            if key in expected_core:assert n==expected_core[key]
            for kind in ['book','scope','handling','knowledge']:
                members=[c for c in cases if c['kind']==kind]
                assert derived['groups'][kind]=={'passed':sum(jud[c['id']]['task_success'] for c in members),'total':len(members)}
            for split in ['core','supplement','all']:
                vals=sorted(r['generation_seconds'] for c,r in zip(cases,run['results']) if split=='all' or c['split']==split)
                # Independent sorted interpolation, not the report's statistics.quantiles implementation.
                def quantile(q):
                    pos=(len(vals)-1)*q;lo=int(pos);hi=min(lo+1,len(vals)-1)
                    return vals[lo]+(pos-lo)*(vals[hi]-vals[lo])
                d=derived['latency'][split]
                for k,q in [('q1',.25),('median',.5),('q3',.75)]:assert abs(d[k]-quantile(q))<1e-9
        matches=sum(a['answer']['content']==b['answer']['content'] for a,b in zip(raw['runs'][0]['results'],raw['runs'][1]['results']))
        assert matches==m['same_answers']
        core_scores[key]=[r['core_passed'] for r in m['runs']]
        if key in expected_core:
            original_cutoffs+=sum(r['finish_reason']=='length' for run in raw['runs'] for r in run['results'])
        else:
            cohort=read(f"data/cohorts/{m['cohort']}.json")
            assert raw['runtime_binary_sha256']==cohort['runtime_binary_sha256']
            assert raw['verified_loaded_weight_sha256']==raw['profile']['sha256']
            assert raw['template_sha256']==hashlib.sha256((ROOT/'templates'/raw['profile']['chat_template']).read_bytes()).hexdigest()
            assert 'completed_utc' in cohort
            assert cohort['settings']['reasoning']=='off' and cohort['settings']['tools'] is False
        for trial,derived in zip(raw['runs'],m['runs']):
            # Verify output compliance measurements, without assuming disabled mode was obeyed.
            markers=sum(bool(re.search(r'</?think\b',r['answer']['content']) or r['answer'].get('reasoning_content')) for r in trial['results'])
            tools=sum(bool(r['answer'].get('tool_calls') or '<tool_call>' in r['answer']['content']) for r in trial['results'])
            assert derived['thinking_markers']==markers and derived['tool_outputs']==tools
    csvrows=list(csv.DictReader((ROOT/'results/measurements.csv').open()))
    assert count==len(csvrows)==len(summary['models'])*80==summary['responses']
    assert len({(r['model'],r['run'],r['question']) for r in csvrows})==count
    assert original_cutoffs==12
    # Check the approved public export; values in third-party model IDs/licenses are technical references.
    forbidden=['/Users/','/home/','drive.google.com','credentials.enc','Bearer sk-','ghp_']
    for name in manifest['sha256']:
        path=ROOT/name
        if path.name=='validate.py':continue
        if path.suffix not in ['.json','.jsonl','.py','.html','.js','.css','.md','.txt','.jinja'] and path.name not in ['LICENSE','.gitignore']:continue
        content=path.read_text()
        for marker in forbidden:
            assert marker not in content,f'Non-public marker in {path.relative_to(ROOT)}'
    return {'status':'passed','pinned_files':len(manifest['sha256']),'core_cases':32,'supplementary_cases':8,
        'measured_responses':count,'length_cutoffs_retained':cutoffs,'core_scores_by_run':core_scores,
        'checks':['file checksums','unchanged original evidence','40 exact prompt hashes','all exact answer review hashes','split denominators',
                  'per-group counts','independent latency quartiles','duplicate-free CSV','synthetic passage labels',
                  'context budgets','repeat equality','bounded private-marker scan'],
        'limits':'Checks do not independently validate every factual judgment or establish production reliability.'}

if __name__=='__main__':print(json.dumps(validate_release(),indent=2))
