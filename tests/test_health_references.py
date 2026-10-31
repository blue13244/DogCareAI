import csv
import hashlib
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from health_guide import related_conditions, triage


class HealthReferenceTests(unittest.TestCase):
    def setUp(self):
        self.record={'식사량':3,'음수량':3,'배뇨량':3,'활동량':3,'수면시간':3,
                     '증상_구토':0,'증상_설사':0,'증상_기침':0,'증상_보행이상':0,'크기':'소형견'}

    def ids(self, **changes):
        return {row['condition_id'] for row in related_conditions({**self.record,**changes})}

    def test_twelve_sourced_references(self):
        with (ROOT/'data/condition_guide.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),12)
        self.assertEqual(len({r['condition_id'] for r in rows}),12)
        domains={'www.merckvetmanual.com','www.vet.cornell.edu','www.acvs.org','vcahospitals.com'}
        self.assertTrue(all(urlparse(r['출처URL']).hostname in domains for r in rows))

    def test_cushing_context(self):
        self.assertIn('C09',self.ids(음수량=4,배뇨량=4,식사량=4))
        self.assertNotIn('C09',self.ids(음수량=4,배뇨량=4,식사량=3))

    def test_pancreatitis_context(self):
        self.assertIn('C10',self.ids(증상_구토=1,식사량=2))
        self.assertNotIn('C10',self.ids(증상_구토=0,식사량=2))

    def test_respiratory_context(self):
        self.assertIn('C11',self.ids(증상_기침=1))
        self.assertNotIn('C11',self.ids())

    def test_patella_context(self):
        self.assertIn('C12',self.ids(증상_보행이상=1))
        self.assertNotIn('C12',self.ids(증상_보행이상=1,크기='대형견'))

    def test_original_reference_rules_preserved(self):
        ids=self.ids(음수량=4,배뇨량=4,증상_구토=1,식사량=2,증상_기침=1,증상_보행이상=1)
        self.assertTrue({'C01','C02','C03','C04','C05','C06','C07'}.issubset(ids))

    def test_urgent_rule_still_precedes_reference_matching(self):
        self.assertEqual(triage(self.record,['호흡곤란'])['level'],'urgent')
        gdv=related_conditions(self.record,['복부팽창과 토하지 못하는 헛구역질'])
        self.assertIn('C08',{r['condition_id'] for r in gdv})

    def test_original_training_data_not_relabelled(self):
        digest=hashlib.sha256((ROOT/'data/dog_data.csv').read_bytes()).hexdigest()
        self.assertEqual(digest,'58e3a8def6a66542fb76c0be61e19720db7146c3a8d4b97fff6559f39fc0a1e8')


if __name__=='__main__':
    unittest.main()

