"""Verify evidence integrity and independently reconcile the public scorecard."""
from collections import Counter
import csv
import hashlib
import json
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
    count=0;cutoffs=0
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
            assert n==derived['core_passed']==expected_core[key] and derived['core_total']==32
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
        assert all(a['answer']['content']==b['answer']['content'] for a,b in zip(raw['runs'][0]['results'],raw['runs'][1]['results']))
    csvrows=list(csv.DictReader((ROOT/'results/measurements.csv').open()))
    assert count==len(csvrows)==480
    assert len({(r['model'],r['run'],r['question']) for r in csvrows})==480
    assert cutoffs==12
    # Check the approved public export; values in third-party model IDs/licenses are technical references.
    forbidden=['/Users/','/home/','drive.google.com','credentials.enc','Bearer sk-','ghp_']
    for path in ROOT.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.name=='validate.py' or '.git' in path.parts:continue
        if path.suffix not in ['.json','.jsonl','.py','.html','.js','.css','.md','.txt','.jinja'] and path.name not in ['LICENSE','.gitignore']:continue
        content=path.read_text()
        for marker in forbidden:
            assert marker not in content,f'Non-public marker in {path.relative_to(ROOT)}'
    return {'status':'passed','pinned_files':len(manifest['sha256']),'core_cases':32,'supplementary_cases':8,
        'measured_responses':count,'length_cutoffs_retained':cutoffs,'core_scores':expected_core,
        'checks':['file checksums','40 exact prompt hashes','480 exact answer review hashes','split denominators',
                  'per-group counts','independent latency quartiles','duplicate-free CSV','synthetic passage labels',
                  'context budgets','repeat equality','bounded private-marker scan'],
        'limits':'Checks do not independently validate every factual judgment or establish production reliability.'}

if __name__=='__main__':print(json.dumps(validate_release(),indent=2))
