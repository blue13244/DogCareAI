import sys
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class AppTests(unittest.TestCase):
    def test_survey_submission_and_safety(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        self.assertEqual(len(app.exception),0)
        self.assertFalse(any('ID' in t.label for t in app.text_input))
        next(s for s in app.slider if s.label=='활동량').set_value(1)
        next(s for s in app.slider if s.label=='수면시간').set_value(4)
        app.multiselect[0].set_value(['호흡곤란'])
        next(b for b in app.button if b.label=='AI로 생활 변화 분석').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('즉시 진료' in x.value for x in app.error))
        saved=app.session_state['analysis']
        self.assertEqual(len(saved['analysis']['neighbors']),5)
        self.assertNotIn('disease_probability', saved['analysis'])
        self.assertEqual(len(saved['comparisons']),12)
        self.assertTrue(any(c['condition_id']=='C06' and c['matched_count']==1 for c in saved['comparisons']))
        self.assertTrue(any('관련 증상 비교' in t.label for t in app.tabs))

    def test_model_page(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        next(r for r in app.radio if r.label=='메뉴').set_value('모델·데이터').run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('100' in str(x.value) for x in app.metric))

    def test_symptom_reference_page(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        menu = next(r for r in app.radio if r.label=='메뉴')
        self.assertNotIn('질병 확률 데이터',menu.options)
        menu.set_value('증상 비교 자료').run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.expander),12)
        self.assertTrue(any('설문을 분석하면' in x.value for x in app.info))


if __name__=='__main__':
    unittest.main()

