"""증상 개수와 미확인을 검증한다. 학습 모델 의존성 없이 실행 가능하다."""
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from symptom_compare import compare_symptoms, comparison_summary, load_profiles
from health_guide import triage, RED_FLAGS


def record(**changes):
    return {"식사량": 3, "음수량": 3, "배뇨량": 3, "활동량": 3, "수면시간": 3,
            "증상_구토": 0, "증상_설사": 0, "증상_기침": 0, "증상_보행이상": 0,
            "나이_세": 10, "체중_kg": 7.3, "크기": "소형견", "약물복용": "X", **changes}


def condition(data, cid, flags=None):
    return next(item for item in compare_symptoms(data, flags) if item["condition_id"] == cid)


class SymptomComparisonTests(unittest.TestCase):
    def test_reference_profiles_are_unique_and_sourced(self):
        data = load_profiles()
        self.assertEqual([p['condition_id'] for p in data['profiles']], [f'C{i:02}' for i in range(1,13)])
        for p in data['profiles']:
            self.assertTrue(p['source_url'].startswith('https://'))
            self.assertTrue(p['source_name'])
            self.assertTrue(p['note'])

    def test_directions_and_unknown_weight_loss(self):
        item = condition(record(음수량=4, 배뇨량=5), 'C01')
        self.assertEqual((item['matched_count'],item['assessed_count'],item['unassessed_count']), (2,3,1))
        self.assertIn('시간에 따른 체중 감소', item['unassessed_signs'])
        self.assertEqual(item['reference_count'],4)

    def test_decrease_does_not_match_increase(self):
        item = condition(record(음수량=1, 배뇨량=2, 식사량=2), 'C01')
        self.assertEqual(item['matched_count'],0)

    def test_each_ordinal_boundary(self):
        for n in range(1,6):
            with self.subTest(n=n):
                self.assertEqual(condition(record(식사량=n),'C01')['matched_count'], int(n>3))
                self.assertEqual(condition(record(식사량=n),'C03')['matched_count'], int(n<3))

    def test_baseline_is_assessed_and_not_a_match(self):
        item = condition(record(),'C03')
        self.assertEqual((item['matched_count'], item['assessed_count'], item['unassessed_count']), (0,4,0))

    def test_digestive_symptoms_match_multiple_profiles(self):
        data = record(식사량=2, 증상_구토=1, 증상_설사=1)
        for cid in ['C03','C04','C10']:
            with self.subTest(cid=cid):
                self.assertEqual(condition(data,cid)['matched_count'],3)
        self.assertEqual(condition(data,'C04')['unassessed_count'],2)
        self.assertEqual(condition(data,'C10')['unassessed_count'],2)

    def test_no_demographic_or_sleep_match(self):
        a = compare_symptoms(record())
        b = compare_symptoms(record(나이_세=18, 체중_kg=1, 크기='대형견', 약물복용='O', 수면시간=5))
        self.assertEqual(a,b)

    def test_flags_unknown_for_csv_and_assessed_for_survey(self):
        csv_item = condition(record(),'C06')
        survey_item = condition(record(),'C06',[])
        self.assertEqual(csv_item['unassessed_count'],2)
        self.assertEqual(survey_item['unassessed_count'],1)
        self.assertEqual(survey_item['assessed_count'],2)

    def test_breathing_does_not_match_panting(self):
        self.assertEqual(condition(record(),'C06',['호흡곤란'])['matched_count'],1)
        self.assertEqual(condition(record(),'C09',['호흡곤란'])['matched_count'],0)
        self.assertIn('헐떡거림', condition(record(),'C09',['호흡곤란'])['unassessed_signs'])

    def test_generic_cough_does_not_confirm_honking(self):
        item = condition(record(증상_기침=1),'C06',[])
        self.assertEqual(item['matched_count'],1)
        self.assertEqual(item['unassessed_count'],1)

    def test_combined_red_flag_is_not_double_counted(self):
        item = condition(record(),'C08',[RED_FLAGS[3]])
        self.assertEqual((item['matched_count'],item['assessed_count'],item['unassessed_count']),(1,2,2))

    def test_generic_gait_does_not_confirm_skipping_or_pain(self):
        item = condition(record(증상_보행이상=1),'C12')
        self.assertEqual((item['matched_count'],item['assessed_count'],item['unassessed_count']),(1,1,2))

    def test_invalid_and_missing_values_stay_unknown(self):
        for value in [None,'',float('nan'),float('inf'),0,6,2.5]:
            with self.subTest(value=value):
                item = condition(record(음수량=value),'C01')
                self.assertEqual(item['unassessed_count'],2)
        self.assertTrue(all(r['unassessed_count']==r['reference_count'] for r in compare_symptoms({})))

    def test_invalid_binary_is_unknown(self):
        item = condition(record(증상_구토=2),'C03')
        self.assertEqual(item['unassessed_count'],1)

    def test_summary_reports_counts_without_percentage(self):
        text = comparison_summary(compare_symptoms(record(음수량=4,배뇨량=4)))
        self.assertIn('비교 3개 중 2개 일치, 미확인 1개',text)
        self.assertNotIn('%',text)
        self.assertNotIn('확률',text)

    def test_no_match_summary_is_not_health_clearance(self):
        self.assertEqual(comparison_summary(compare_symptoms(record())), '비교 가능한 항목에서 일치 징후 없음')

    def test_results_preserve_reference_order(self):
        results = compare_symptoms(record(증상_기침=1,식사량=5))
        self.assertEqual([r['condition_id'] for r in results], [f'C{i:02}' for i in range(1,13)])

    def test_counts_partition_selected_signs(self):
        for item in compare_symptoms(record(증상_구토=1,음수량=4),[]):
            self.assertEqual(item['assessed_count']+item['unassessed_count'], item['reference_count'])
            self.assertLessEqual(item['matched_count'],item['assessed_count'])
            self.assertFalse(any(key in item for key in ['probability','risk','score','percent']))

    def test_red_flags_keep_triage_regardless_of_comparison_count(self):
        for flag in RED_FLAGS:
            with self.subTest(flag=flag):
                self.assertEqual(triage(record(),[flag])['level'],'urgent')

    def test_reject_invalid_flag_type(self):
        with self.assertRaises(ValueError):
            compare_symptoms(record(),'호흡곤란')

    def test_reject_duplicate_reference_item(self):
        data = load_profiles()
        data['profiles'][0]['symptoms'].append(data['profiles'][0]['symptoms'][0])
        with patch('symptom_compare.Path.read_text', return_value=json.dumps(data)):
            with self.assertRaises(ValueError):
                load_profiles()


if __name__ == '__main__':
    unittest.main()

