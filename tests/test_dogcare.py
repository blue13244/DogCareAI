import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core
from health_guide import triage, RED_FLAGS, related_conditions, age_guidance, size_guidance


class DogCareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = core.read_data(training=True)
        cls.bundle, _ = core.get_bundle()
        cls.record = cls.data.iloc[0][core.FEATURES].to_dict()

    def test_training_data(self):
        self.assertGreaterEqual(len(self.data), 100)
        self.assertEqual(set(self.data['데이터구분']), {'가상_데모'})
        self.assertEqual(self.data[core.TARGET].value_counts().to_dict(), {'정상':38,'관찰 필요':31,'건강 이상 의심':31})

    def test_saved_model_matches_data(self):
        self.assertEqual(self.bundle['data_sha256'], core.file_digest())
        self.assertEqual(self.bundle['schema_version'], core.SCHEMA_VERSION)

    def test_invalid_scores(self):
        for value in ['',0,6,2.5,float('nan'),float('inf')]:
            frame = pd.DataFrame([{**self.record, '식사량':value}])
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.validate_data(frame)

    def test_missing_features(self):
        with self.assertRaises(ValueError):
            core.validate_data(pd.DataFrame([self.record]).drop(columns=['음수량']))

    def test_binary_symptoms(self):
        with self.assertRaises(ValueError):
            core.validate_data(pd.DataFrame([{**self.record,'증상_구토':2}]))

    def test_invalid_metadata(self):
        for changes in [{'크기':'알수없음'}, {'약물복용':'Y'}, {'체중_kg':0}, {'나이_세':-1}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                core.validate_data(pd.DataFrame([{**self.record, **changes}]))

    def test_no_label_leakage(self):
        used = list(self.bundle['classifier'].feature_names_in_)
        self.assertEqual(used, core.FEATURES)
        self.assertTrue(set(used).isdisjoint(['ID','이름',core.TARGET,'판단주요특징','추가증상','데이터구분']))

    def test_predictions_use_learned_models(self):
        result = core.analyze_record(self.record, self.bundle)
        frame = pd.DataFrame([self.record])
        self.assertEqual(result['virtual_label'], self.bundle['classifier'].predict(frame[core.FEATURES])[0])
        expected = int(self.bundle['clusterer'].predict(self.bundle['embedding'].transform(frame[core.FEATURES]))[0])
        self.assertEqual(result['pattern']['cluster'], expected)

    def test_no_fabricated_disease_probability(self):
        p = core.analyze_record(self.record, self.bundle)['disease_probability']
        self.assertFalse(p['available'])
        self.assertIsNone(p['value'])

    def test_nearest_cases_and_exclusion(self):
        result = core.analyze_record(self.record, self.bundle, exclude_id='D01')
        cases = result['neighbors']
        self.assertEqual(len(cases),5)
        self.assertTrue(cases['사례ID'].is_unique)
        self.assertNotIn('D01',cases['사례ID'].tolist())
        self.assertTrue(cases['모델거리'].is_monotonic_increasing)

    def test_weight_from_csv(self):
        w = core.weight_comparison(self.record, self.data)
        expected = self.data.loc[self.data['크기']==self.record['크기'],'체중_kg']
        self.assertAlmostEqual(w['mean_kg'],expected.mean())
        self.assertEqual(w['count'],len(expected))

    def test_id_and_exact_feature_groups(self):
        data = self.data.copy()
        data.loc[1,'ID'] = data.loc[0,'ID']
        data.loc[2,core.FEATURES] = data.loc[1,core.FEATURES].values
        groups = core.split_groups(data)
        self.assertEqual(groups[0],groups[1])
        self.assertEqual(groups[1],groups[2])

    def test_cv_groups_do_not_overlap(self):
        metrics = self.bundle['metrics']
        self.assertTrue(all(f['overlapping_groups']==0 for f in metrics['folds']))
        self.assertEqual(sum(f['test_rows'] for f in metrics['folds']),len(self.data))
        self.assertGreaterEqual(metrics['cv_folds'],2)

    def test_urgent_overrides_normal_case(self):
        # 첫 기록은 정상 가상 라벨이지만 긴급 징후가 있으면 즉시 진료를 안내한다.
        for flag in RED_FLAGS:
            with self.subTest(flag=flag):
                self.assertEqual(triage(self.record,[flag])['level'],'urgent')

    def test_persistent_symptoms_guidance(self):
        self.assertEqual(triage({**self.record,'증상_구토':1}, duration_hours=24)['level'],'soon')
        self.assertEqual(triage(self.record,persistent_cough=True)['level'],'soon')

    def test_conditions_are_contextual_and_sourced(self):
        input_record = {**self.record,'크기':'소형견','증상_기침':1,'음수량':4,'배뇨량':4}
        conditions = related_conditions(input_record)
        self.assertIn('C06',[c['condition_id'] for c in conditions])
        self.assertIn('C01',[c['condition_id'] for c in conditions])
        self.assertTrue(all(c['출처URL'].startswith('https://') for c in conditions))
        self.assertNotIn('C08',[c['condition_id'] for c in conditions])
        self.assertIn('C08',[c['condition_id'] for c in related_conditions(input_record,[RED_FLAGS[3]])])

    def test_context_guides(self):
        self.assertIn('성장',age_guidance(0.5,'대형견')[0])
        self.assertIn('가슴',size_guidance('대형견')[0])

    def test_batch_predictions(self):
        out = core.batch_analyze(self.data.head(5),self.bundle)
        self.assertEqual(len(out),5)
        self.assertTrue(out['실제질병확률'].str.startswith('산출 불가').all())

    def test_bad_provenance_not_accepted(self):
        data = self.data.copy(); data.loc[0,'데이터구분']='실제_확진'
        with self.assertRaises(ValueError):
            core.validate_data(data,training=True)


if __name__=='__main__':
    unittest.main()
