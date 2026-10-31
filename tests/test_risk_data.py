"""발병 기록의 구조 점검 테스트. 아래 기록은 테스트용이며 실제 임상 자료가 아니다."""
import csv
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from risk_data import audit_csv, outcome_for_horizon, template_bytes, TEMPLATE_FIELDS


class RiskDataTests(unittest.TestCase):
    def setUp(self):
        self.record = {"개체ID":"TEST_ONLY", "기준일":"2026-01-01", "질환코드":"TEST_DISEASE",
            "기준일질환없음확인":"1", "추적종료일":"2026-05-01", "발병여부":"0", "확진일":"",
            "확인근거":"테스트 픽스처", "자료출처":"실제 자료 아님: 단위 테스트", "데이터구분":"실제_관찰",
            "나이_세":"5", "체중_kg":"7", "크기":"소형견", "약물복용":"X",
            "식사량":"3", "음수량":"3", "배뇨량":"3", "활동량":"3", "수면시간":"3",
            "증상_구토":"0", "증상_설사":"0", "증상_기침":"0", "증상_보행이상":"0"}

    def csv_bytes(self, rows):
        out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=TEMPLATE_FIELDS)
        writer.writeheader(); writer.writerows(rows)
        return out.getvalue().encode('utf-8-sig')

    def test_current_data_has_no_clinical_outcomes(self):
        report = audit_csv(ROOT/'data/dog_data.csv')
        self.assertEqual(report['rows'],100)
        self.assertEqual(report['columns'],19)
        self.assertEqual(report['synthetic_rows'],100)
        self.assertIn('확진일',report['missing_fields'])
        self.assertNotIn('개체ID',report['missing_fields'])
        self.assertFalse(report['probability_available'])

    def test_template_has_no_invented_records(self):
        fields = template_bytes().decode('utf-8-sig').splitlines()
        self.assertEqual(len(fields),1)
        self.assertIn('확진일',fields[0])
        template = ROOT/'data/clinical_outcomes_template.csv'
        self.assertEqual(next(csv.reader(io.StringIO(template.read_text(encoding='utf-8-sig')))),TEMPLATE_FIELDS)

    def test_full_followup_negative(self):
        self.assertEqual(outcome_for_horizon(self.record,90)['target'],0)

    def test_censored_is_not_negative(self):
        result = outcome_for_horizon({**self.record,'추적종료일':'2026-01-15'},90)
        self.assertEqual(result['status'],'censored')
        self.assertIsNone(result['target'])

    def test_confirmed_event_within_horizon(self):
        result = outcome_for_horizon({**self.record,'발병여부':'1','확진일':'2026-02-01'},90)
        self.assertEqual(result['target'],1)

    def test_event_after_horizon_not_future_leakage(self):
        result = outcome_for_horizon({**self.record,'발병여부':'1','확진일':'2026-04-20'},90)
        self.assertEqual(result['target'],0)

    def test_invalid_event_date_rejected(self):
        with self.assertRaises(ValueError):
            outcome_for_horizon({**self.record,'발병여부':'1','확진일':'2025-12-30'},90)

    def test_synthetic_records_rejected(self):
        with self.assertRaises(ValueError):
            outcome_for_horizon({**self.record,'데이터구분':'가상_데모'},90)

    def test_preexisting_disease_not_incident(self):
        result = outcome_for_horizon({**self.record,'기준일질환없음확인':'0'},90)
        self.assertIsNone(result['target'])

    def test_duplicate_records_not_extra_evidence(self):
        report = audit_csv(self.csv_bytes([self.record,self.record]))
        self.assertEqual(report['outcome_counts']['invalid'],1)

    def test_formatted_data_does_not_enable_probabilities(self):
        report = audit_csv(self.csv_bytes([self.record]))
        self.assertEqual(report['outcome_counts']['observed_no_event'],1)
        self.assertFalse(report['probability_available'])

    def test_blank_predictor_not_imputed(self):
        report = audit_csv(self.csv_bytes([{**self.record,'음수량':''}]))
        self.assertEqual(report['outcome_counts']['invalid'],1)


if __name__=='__main__':
    unittest.main()

