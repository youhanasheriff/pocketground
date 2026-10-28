"""Rebuild the public scorecard and standalone viewer from frozen evidence."""
from collections import Counter
import csv
import json
from pathlib import Path
import re
import statistics

from pocketground import DATA, ROOT, read, score, validate_dataset

def distribution(values):
    q1, median, q3 = statistics.quantiles(values, n=4, method='inclusive')
    return {'n':len(values), 'min':min(values), 'q1':q1, 'median':median, 'q3':q3, 'max':max(values)}

def build():
    dataset = validate_dataset(read(DATA / 'dataset.json'))
    metadata = read(ROOT / 'data/models.json')
    models = []
    csvrows = []
    for meta in metadata:
        raw = read(ROOT / f"results/reference/{meta['key']}.json")
        review = read(ROOT / f"results/reference/{meta['key']}.review.json")
        checked = score(dataset, raw, review)
        model = {**meta, 'runs':[]}
        for trial, scored in zip(raw['runs'], checked['runs']):
            judgments = review['runs'][str(trial['run'])]
            answers = {}
            for record in trial['results']:
                c = next(c for c in dataset['cases'] if c['id'] == record['id'])
                j = judgments[c['id']]
                content = record['answer']['content']
                refs = sorted(set(map(int, re.findall(r'\[P(\d+)\]', content))))
                answers[c['id']] = {'content':content, 'seconds':record['generation_seconds'],
                    'prompt_tokens':record['usage']['prompt_tokens'], 'output_tokens':record['usage']['completion_tokens'],
                    'decode_tps':record['timings']['predicted_per_second'], 'finish_reason':record['finish_reason'],
                    'task_success':j['task_success'], 'factual_status':j['factual_status'],
                    'provenance_pass':j['provenance_pass'], 'note':j['note'], 'refs':refs,
                    'thinking_marker':bool(re.search(r'</?think\b',content) or record['answer'].get('reasoning_content')),
                    'tool_output':bool(record['answer'].get('tool_calls') or '<tool_call>' in content)}
                csvrows.append({'model':meta['key'], 'run':trial['run'], 'question':c['id'], 'split':c['split'], 'group':c['kind'],
                    'task_success':j['task_success'], 'factual_status':j['factual_status'], 'source_disclosure':j['provenance_pass'],
                    'api_seconds':record['generation_seconds'], 'output_tokens':record['usage']['completion_tokens'],
                    'finish_reason':record['finish_reason'], 'thinking_marker':answers[c['id']]['thinking_marker'],
                    'tool_output':answers[c['id']]['tool_output']})
            selected = lambda split: [answers[c['id']] for c in dataset['cases'] if split == 'all' or c['split'] == split]
            model['runs'].append({**scored, 'answers':answers,
                'latency':{s:distribution([a['seconds'] for a in selected(s)]) for s in ['core','supplement','all']},
                'median_output_tokens':{s:statistics.median(a['output_tokens'] for a in selected(s)) for s in ['core','supplement','all']},
                'book_factual':dict(Counter(answers[c['id']]['factual_status'] for c in dataset['cases'] if c['kind']=='book')),
                'knowledge_factual':dict(Counter(answers[c['id']]['factual_status'] for c in dataset['cases'] if c['kind']=='knowledge')),
                'book_citation_presence':sum(bool(answers[c['id']]['refs']) for c in dataset['cases'] if c['kind']=='book'),
                'knowledge_disclosure':sum(answers[c['id']]['provenance_pass'] is True for c in dataset['cases'] if c['kind']=='knowledge')})
            model['runs'][-1]['thinking_markers']=sum(a['thinking_marker'] for a in answers.values())
            model['runs'][-1]['tool_outputs']=sum(a['tool_output'] for a in answers.values())
        model['same_answers'] = sum(model['runs'][0]['answers'][c['id']]['content'] == model['runs'][1]['answers'][c['id']]['content'] for c in dataset['cases'])
        models.append(model)
    version=(ROOT/'VERSION').read_text().strip()
    summary = {'benchmark':'PocketGround', 'version':version, 'dataset':dataset['suite'],
        'core':32, 'supplement':8, 'responses':len(csvrows), 'models':[
            {'key':m['key'], 'name':m['name'], 'cohort':m['cohort'], 'bytes':m['profile']['bytes'], 'budget_eligible':m['budget_eligible'],
             'same_answers':m['same_answers'],
             'runs':[{k:r[k] for k in ['run','groups','core_passed','core_total','latency','length_cutoffs','book_citation_presence','knowledge_disclosure','thinking_markers','tool_outputs']} for r in m['runs']]}
            for m in models]}
    (ROOT / 'results/scorecard.json').write_text(json.dumps(summary, indent=2)+'\n')
    with (ROOT / 'results/measurements.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(csvrows[0]),lineterminator='\n');writer.writeheader();writer.writerows(csvrows)
    # Repeated passages are stored once in the portable viewer. Full messages remain in dataset.json.
    passages = {}
    cases = []
    for c in dataset['cases']:
        ids=[]
        for p in c['passages']:
            k=str(p['id']);clean={key:p[key] for key in ['id','pdf_page','text','synthetic'] if key in p}
            assert passages.setdefault(k,clean)==clean
            ids.append(k)
        cases.append({k:c[k] for k in ['id','kind','split','short','question','expected','expected_pages','prompt_sha256']} | {'passages':ids})
    payload = {'version':version,'cases':cases,'passages':passages,'models':models,
        'protocol':read(DATA/'protocol.json'), 'source':read(DATA/'source.json'),
        'cohorts':{p.stem:read(p) for p in (ROOT/'data/cohorts').glob('*.json')},
        'external':read(DATA/'external-references.json'), 'system_prompt':dataset['system_prompt']}
    # Share repeated answer text across runs without changing the full raw evidence.
    answer_pool={}
    for model in payload['models']:
        for run in model['runs']:
            for answer in run['answers'].values():
                content=answer.pop('content')
                identity=str(len(answer_pool)) if content not in answer_pool else answer_pool[content]
                answer_pool[content]=identity
                answer['content_id']=identity
    payload['answer_pool']={identity:content for content,identity in answer_pool.items()}
    template=(ROOT/'viewer/index.html').read_text()
    for marker,value in [('__CSS__',(ROOT/'viewer/style.css').read_text()),
        ('__DATA__',json.dumps(payload,separators=(',',':')).replace('<','\\u003c')),
        ('__JS__',"for(const m of D.models){for(const r of m.runs){for(const a of Object.values(r.answers)){a.content=D.answer_pool[a.content_id];}}}\n"+(ROOT/'viewer/report.js').read_text())]:
        assert template.count(marker)==1
        template=template.replace(marker,value)
    (ROOT/'reports/index.html').write_text(template)
    (ROOT/'docs/index.html').write_text(template)
    (ROOT/'docs/detailed-40.html').write_bytes((ROOT/'reports/detailed-40.html').read_bytes())
    print(f"Built reports/index.html: {len(template.encode()):,} bytes; {len(csvrows)} measured responses.")

if __name__=='__main__':build()
