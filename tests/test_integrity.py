"""Guard the failure modes that could silently change benchmark claims."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pocketground import DATA, ROOT, message_hash, read, request, score, validate_dataset, write_new

class EvidenceIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset=read(DATA/'dataset.json')
        cls.raw=read(ROOT/'results/reference/q4.json')
        cls.review=read(ROOT/'results/reference/q4.review.json')

    def test_original_counts_and_supplement_exclusion(self):
        result=score(self.dataset,self.raw,self.review)
        for r in result['runs']:
            self.assertEqual((r['core_passed'],r['core_total']),(28,32))
            self.assertEqual(r['groups']['knowledge'],{'passed':2,'total':8})

    def test_changed_answer_cannot_reuse_review(self):
        raw=copy.deepcopy(self.raw);raw['runs'][0]['results'][0]['answer']['content']+=' changed'
        with self.assertRaisesRegex(ValueError,'Stale'):score(self.dataset,raw,self.review)

    def test_changed_prompt_is_rejected(self):
        data=copy.deepcopy(self.dataset);data['cases'][0]['messages'][1]['content']+=' changed'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):validate_dataset(data)

    def test_duplicate_or_missing_case_is_rejected(self):
        for mode in ['duplicate','missing']:
            raw=copy.deepcopy(self.raw)
            if mode=='duplicate':raw['runs'][0]['results'][1]=raw['runs'][0]['results'][0]
            else:raw['runs'][0]['results'].pop()
            with self.assertRaisesRegex(ValueError,'Incomplete'):score(self.dataset,raw,self.review)

    def test_unreviewed_task_is_rejected(self):
        j=copy.deepcopy(self.review);j['runs']['1']['alarm_test']['task_success']=None
        with self.assertRaisesRegex(ValueError,'manual judgment'):score(self.dataset,self.raw,j)

    def test_duplicate_run_id_is_rejected(self):
        raw=copy.deepcopy(self.raw);raw['runs'][1]['run']=1
        with self.assertRaisesRegex(ValueError,'run IDs'):score(self.dataset,raw,self.review)

    def test_failed_task_requires_reason(self):
        j=copy.deepcopy(self.review);j['runs']['1']['pass']['note']=''
        with self.assertRaisesRegex(ValueError,'Explain'):score(self.dataset,self.raw,j)

    def test_separate_schedule_scores_only_its_cases(self):
        core={c['id'] for c in self.dataset['cases'] if c['split']=='core'}
        raw=copy.deepcopy(self.raw);raw['split']='core'
        for r in raw['runs']:r['results']=[v for v in r['results'] if v['id'] in core]
        result=score(self.dataset,raw,self.review)
        self.assertEqual(result['runs'][0]['groups']['knowledge'],{'passed':0,'total':0})
        self.assertEqual(result['runs'][0]['core_passed'],28)

    def test_api_errors_are_not_model_failures(self):
        raw=copy.deepcopy(self.raw);raw['runs'][0]['results'][0]['error']='connection failed'
        with self.assertRaisesRegex(ValueError,'API failure'):score(self.dataset,raw,self.review)

    def test_export_does_not_overwrite_previous_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'review.json';write_new(p,{'saved':True})
            with self.assertRaises(FileExistsError):write_new(p,{'saved':False})
            self.assertTrue(read(p)['saved'])

    def test_both_api_base_url_forms_and_secret_not_in_payload(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self):return b'{"choices":[]}'
        for base in ['http://localhost:1234','http://localhost:1234/v1/']:
            with patch('urllib.request.urlopen',return_value=Response()) as mocked, patch.dict('os.environ',{'TEST_KEY':'test-only-value'}):
                request(base,{'model':'test-model'},10,'TEST_KEY')
                sent=mocked.call_args.args[0]
                self.assertEqual(sent.full_url,'http://localhost:1234/v1/chat/completions')
                self.assertEqual(sent.get_header('Authorization'),'Bearer test-only-value')
                self.assertNotIn(b'test-only-value',sent.data)

    def test_new_checkpoint_reviews_are_bound_to_every_returned_answer(self):
        for key,expected in [('q4_current',28),('lfm3_text',24),('lfm3_omni',28)]:
            raw=read(ROOT/f'results/reference/{key}.json')
            reviewed=read(ROOT/f'results/reference/{key}.review.json')
            result=score(self.dataset,raw,reviewed)
            self.assertEqual([r['core_passed'] for r in result['runs']],[expected,expected])
            self.assertEqual([len(r['results']) for r in raw['runs']],[40,40])

    def test_original_snapshot_is_not_changed_by_new_comparisons(self):
        for filename,expected in read(ROOT/'data/original-snapshot.json')['unchanged_files'].items():
            self.assertEqual(hashlib.sha256((ROOT/filename).read_bytes()).hexdigest(),expected)

    def test_streamed_weight_hash_matches_standard_digest(self):
        from run_local_models import file_sha256
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'weights.bin';p.write_bytes(b'pin this exact weight file'*900000)
            self.assertEqual(file_sha256(p),hashlib.sha256(p.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
