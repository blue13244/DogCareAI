"""Streamlit Community Cloud 진입점: app.py"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core import (DATA_PATH, MODEL_PATH, SCORES, SYMPTOMS, LABELS, FEATURES,
                  get_bundle, file_digest, analyze_record, batch_analyze, read_data)
from health_guide import (RED_FLAGS, SOURCES, triage, related_conditions,
                          size_guidance, age_guidance, daily_care)

st.set_page_config(page_title="DogCare AI · 생활 변화 기록", page_icon="🐾", layout="wide")
st.html("""<style>
.block-container {max-width:1120px;padding-top:2rem;padding-bottom:4rem;}
h1 {letter-spacing:-.045em;font-weight:750!important;}
h2,h3 {letter-spacing:-.035em;}
[data-testid="stForm"] {background:#fff;border:1px solid #DDE5DB;border-radius:18px;padding:1.5rem;}
[data-testid="stMetric"] {padding:1.05rem;background:#EDF3EE;border-radius:12px;}
.brand-kicker {font-size:.76rem;letter-spacing:.15em;color:#526B60;font-weight:700;margin-bottom:.8rem;}
.hero-copy {font-size:1.05rem;color:#526B60;max-width:650px;line-height:1.8;}
</style>""")


@st.cache_resource(show_spinner="100건의 학습 모델을 준비하고 있습니다…")
def cached_bundle(csv_hash, model_stamp):
    return get_bundle()


try:
    stamp = MODEL_PATH.stat().st_mtime_ns if MODEL_PATH.exists() else 0
    bundle, model_origin = cached_bundle(file_digest(), stamp)
except (ValueError, OSError, ImportError) as exc:
    st.error(f"모델 준비에 실패했습니다: {exc}")
    st.info("저장소의 requirements.txt와 data/dog_data.csv를 확인하고 python train.py로 다시 학습해 주세요.")
    st.stop()

with st.sidebar:
    st.markdown("### DogCare AI")
    page = st.radio("메뉴", ["강아지 상태 설문", "CSV 일괄 분석", "모델·데이터", "사용 안내"], label_visibility="collapsed")
    st.divider()
    st.caption(f"학습 자료 {len(bundle['records'])}건 · 가상 데모")
    st.caption("생활 패턴과 비슷한 사례를 확인하는 교육용 프로젝트입니다.")
    st.link_button("GitHub 프로젝트", "https://github.com/blue13244/DogCareAI")

st.html('<div class="brand-kicker">DOGCARE AI / EVERYDAY OBSERVATIONS</div>')
st.title("작은 변화를 기록하고,\n생활 패턴을 살펴보세요.")
st.html('<div class="hero-copy">평소와 비교한 설문을 바탕으로 학습한 생활 패턴과 유사 사례를 확인합니다. 건강 참고정보에는 연결 이유와 출처를 함께 표시합니다.</div>')
st.caption("100건의 가상 사례로 학습한 모델입니다. 질병을 진단하거나 실제 질병 발생 확률을 계산하지 않습니다.")


def source_link(source):
    st.markdown(f"[참고: {source[0]}]({source[1]})")


def render_result(saved):
    record, result, safety = saved["record"], saved["analysis"], saved["safety"]
    st.divider()
    st.header("분석 결과")
    if safety["level"] == "urgent":
        st.error(safety["title"] + " " + safety["reason"])
    elif safety["level"] == "soon":
        st.warning(safety["title"] + " " + safety["reason"])
    else:
        st.info(safety["title"] + " " + safety["reason"])
    source_link(safety["source"])
    st.subheader(result["virtual_label_display"])
    st.caption(f"학습 자료의 가상 라벨: {result['virtual_label']}. 이 분류는 건강 정상 여부나 진료 필요성의 판단이 아닙니다.")
    a,b,c = st.columns(3)
    a.metric("학습된 생활 군집", result["pattern"]["name"])
    b.metric("같은 군집의 가상 사례", f"{result['pattern']['rows']}건")
    c.metric("비교할 유사 사례", f"{len(result['neighbors'])}건")
    pattern_tab, similar_tab, health_tab, profile_tab = st.tabs(["생활 변화 패턴", "유사 사례 비교", "건강 참고정보", "체중·나이·크기"])
    with pattern_tab:
        st.write("**이번 입력에서 보고한 변화**")
        for text in result["changes"]:
            st.write("• " + text)
        comparison = pd.DataFrame({"내 응답": [record[c] for c in SCORES],
                                   "같은 군집 평균": [result["pattern"]["means"][c] for c in SCORES]}, index=SCORES)
        st.bar_chart(comparison, horizontal=True, color=["#246C59", "#A5BDB0"])
        st.caption("3은 평소와 같음입니다. 응답은 순서형 점수이며 양·시간의 실제 비율을 뜻하지 않습니다. 군집은 학습 자료에서 찾은 그룹입니다.")
    with similar_tab:
        st.write("학습된 입력 표현에서 가까운 가상 사례를 보여 줍니다.")
        st.dataframe(result["neighbors"], hide_index=True, width="stretch")
        st.caption("모델거리는 작을수록 입력 특징이 가깝다는 뜻입니다. 유사도나 질병 발생 확률의 백분율이 아닙니다. 나이·체중·크기·복용 여부·설문·추가 증상을 함께 비교합니다.")
    with health_tab:
        st.write("**입력한 징후와 관련해 살펴볼 수 있는 질환 참고정보**")
        st.caption("아래 연결은 고정된 증상 조건과 문헌을 이용합니다. 질환 순위·확률·진단 결과가 아니며 표시되지 않은 질환도 있을 수 있습니다.")
        conditions = saved["conditions"]
        if not conditions:
            st.write("현재 입력과 연결되는 참고 항목이 없습니다. 건강 이상이 없다는 의미는 아닙니다.")
        for item in conditions:
            with st.expander(item["참고질환"], expanded=safety["level"] == "urgent"):
                st.write("연결 이유: " + item["연결이유"])
                st.write(item["확인정보"])
                source_link((item["출처명"], item["출처URL"]))
        st.divider()
        st.write("**실제 질병 발생 확률: 산출할 수 없음**")
        st.write(result["disease_probability"]["reason"])
        st.write("**생활 관리와 상담 준비**")
        for text in daily_care(record):
            st.write("• " + text)
        source_link(SOURCES["weight"])
    with profile_tab:
        w = result["weight"]
        if w:
            st.subheader("같은 크기의 가상 자료와 체중 비교")
            a,b,c = st.columns(3)
            a.metric("입력 체중", f"{record['체중_kg']:.1f} kg")
            b.metric(f"{w['size']} {w['count']}건 평균", f"{w['mean_kg']:.1f} kg")
            c.metric("평균과의 차이", f"{w['difference_kg']:+.1f} kg")
            st.caption(w["scope"])
            source_link(SOURCES["weight"])
        st.subheader("크기에 따른 참고정보")
        text, source = size_guidance(record["크기"])
        st.write(text); source_link(source)
        st.subheader("나이에 따른 관리정보")
        text, source = age_guidance(record["나이_세"], record["크기"])
        st.write(text); source_link(source)
        if record.get("견종"):
            st.caption("입력한 견종은 기록에 보존합니다. 학습 자료에 견종 열이 없어 견종별 위험도 계산에는 사용하지 않습니다.")
    export = {**record, "AI가상라벨": result["virtual_label"], "생활패턴": result["pattern"]["name"],
              "변화요약": ", ".join(result["changes"]), "진료안내": safety["title"],
              "참고질환": "; ".join(i["참고질환"] for i in saved["conditions"]),
              "실제질병발생확률": "산출 불가", "학습자료구분": "가상_데모"}
    st.download_button("분석 기록 CSV 내려받기", pd.DataFrame([export]).to_csv(index=False).encode("utf-8-sig"), "DogCareAI_result.csv", "text/csv")


if page == "강아지 상태 설문":
    st.header("강아지 상태 설문")
    with st.form("dog_survey"):
        st.subheader("기본 정보")
        a,b,c = st.columns(3)
        name = a.text_input("이름", value="루이", max_chars=40)
        breed = b.text_input("견종 (선택)", placeholder="예: 믹스견", max_chars=40)
        size = c.selectbox("크기", ["소형견", "중형견", "대형견"])
        age = a.number_input("나이 (세)", min_value=0.0, max_value=35.0, value=10.0, step=0.5)
        weight = b.number_input("체중 (kg)", min_value=0.1, max_value=150.0, value=7.3, step=0.1)
        medicine = c.radio("약물복용", ["X", "O"], horizontal=True)
        st.subheader("평소와 비교한 생활 변화")
        st.caption("1 많이 감소 · 2 조금 감소 · 3 평소와 같음 · 4 조금 증가 · 5 많이 증가")
        values = {field: st.slider(field, 1, 5, 3, help="이 강아지의 평소 생활과 같은 관찰 기간을 기준으로 비교하세요.") for field in SCORES}
        st.caption("관찰하지 못한 항목을 3으로 대신 입력하지 마세요. 모든 항목을 관찰한 뒤 분석해 주세요.")
        st.subheader("추가 증상")
        columns = st.columns(4)
        symptoms = {field: int(columns[i].checkbox(field.replace("증상_", ""))) for i,field in enumerate(SYMPTOMS)}
        with st.expander("진료 안내를 위한 추가 확인", expanded=True):
            red_flags = st.multiselect("현재 아래 증상이 있나요?", RED_FLAGS,
                                       help="선택한 긴급 증상은 AI의 가상 분류 결과와 별도로 우선 안내합니다.")
            duration = st.selectbox("추가 증상의 지속 시간", ["해당 없음 또는 모름", "24시간 미만", "24시간 이상"])
            persistent = st.checkbox("기침이 계속되거나 반복됨")
        submitted = st.form_submit_button("AI로 생활 변화 분석", type="primary", width="stretch")
    if submitted:
        record = {"이름": name, "견종": breed, "나이_세": age, "체중_kg": weight,
                  "크기": size, "약물복용": medicine, **values, **symptoms}
        try:
            result = analyze_record(record, bundle)
            safety = triage(record, red_flags, duration_hours=24 if duration=="24시간 이상" else 0, persistent_cough=persistent)
            st.session_state.analysis = {"record": record, "analysis": result, "safety": safety,
                                         "conditions": related_conditions(record, red_flags)}
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    if "analysis" in st.session_state:
        render_result(st.session_state.analysis)

elif page == "CSV 일괄 분석":
    st.header("CSV 일괄 분석")
    st.write("학습에 사용한 것과 같은 13개 입력 열이 있는 CSV를 올리세요. 라벨과 ID가 없어도 분석할 수 있습니다.")
    st.caption("이 화면은 가상 분류·군집 분석용입니다. CSV에는 긴급 증상·지속 시간 입력이 없으므로 개별 진료 안내는 설문에서 확인하세요.")
    uploaded = st.file_uploader("분석할 CSV", type=["csv"])
    if uploaded:
        try:
            data = read_data(uploaded)
            result = batch_analyze(data, bundle)
            st.dataframe(result, hide_index=True, width="stretch")
            st.download_button("일괄 분석 CSV 내려받기", result.to_csv(index=False).encode("utf-8-sig"), "DogCareAI_batch.csv", "text/csv")
        except (ValueError, OSError, pd.errors.ParserError) as exc:
            st.error(str(exc))

elif page == "모델·데이터":
    st.header("모델과 학습 데이터")
    m = bundle["metrics"]
    st.write(f"사용 중인 모델: {model_origin}")
    st.write("Random Forest 분류, K-Means 생활 군집, Nearest Neighbors 유사 사례 검색이 설문 결과에 실제로 사용됩니다.")
    st.info(m["interpretation"])
    a,b,c = st.columns(3)
    a.metric("가상 학습 기록", f"{m['rows']}건")
    b.metric("그룹 교차검증 정확도", f"{m['oof_accuracy']:.1%}")
    c.metric("Macro F1", f"{m['oof_macro_f1']:.3f}")
    st.caption(f"{m['cv_folds']}개 분할 · 최빈 라벨 기준선 {m['baseline_accuracy']:.1%}. 동일 ID 또는 동일 입력은 같은 그룹에 묶어 학습과 평가에 나뉘지 않게 했습니다.")
    st.write(m["deployment_model"])
    counts = pd.DataFrame({"가상 라벨": list(m["class_counts"]), "건수": list(m["class_counts"].values())})
    st.bar_chart(counts.set_index("가상 라벨"), color="#246C59")
    with st.expander("라벨별 성능과 혼동행렬"):
        report = {k:v for k,v in m["classification_report"].items() if isinstance(v,dict)}
        st.dataframe(pd.DataFrame(report).T)
        st.write("행: 정답 / 열: 예측")
        st.dataframe(pd.DataFrame(m["confusion_matrix"], index=LABELS, columns=LABELS))
    with st.expander("학습 변수와 제외한 정보"):
        st.write("학습 입력: " + ", ".join(FEATURES))
        st.write("제외: " + ", ".join(m["excluded_columns"]))
        st.caption("정답을 설명하는 텍스트, 이름, ID를 분류기에 넣지 않습니다. ID는 평가 분할에만 사용합니다.")
    with st.expander("군집별 요약"):
        st.dataframe(pd.DataFrame([{k:v for k,v in p.items() if k!='means'} for p in bundle["profiles"]]), hide_index=True)
    with st.expander("가상 학습 자료 확인"):
        st.dataframe(bundle["records"].drop(columns=["이름"]), hide_index=True, width="stretch")
    st.download_button("모델 평가 JSON 내려받기", json.dumps(m, ensure_ascii=False, indent=2), "DogCareAI_metrics.json", "application/json")

else:
    st.header("사용 안내")
    st.markdown("""1. 강아지 기본 정보와 평소 대비 생활 변화를 입력합니다.
2. 추가 증상과 긴급 징후를 확인합니다.
3. 분석 버튼을 눌러 생활 군집, 가상 사례 유형, 가까운 사례를 봅니다.
4. 연결 이유와 출처가 표시된 건강 참고정보를 읽고 필요한 내용을 상담에 활용합니다.

입력 내용은 파일이나 데이터베이스에 자동으로 저장하지 않습니다. 필요한 경우 결과 CSV를 직접 내려받을 수 있습니다.

**실제 질병 발생 확률을 제공하지 않는 이유**

현재 자료는 확진·추적 결과가 없는 가상 사례입니다. 모델의 가상 라벨 분류값, 군집 거리, 유사 사례의 라벨 비율을 질병 확률로 바꿔 표시하지 않습니다. 실제 발병 예측은 질환별 확진 결과, 기준 시점, 추적 기간, 대표성 있는 실제 자료와 독립 검증이 필요합니다.
""")
    st.link_button("전체 코드와 배포 설명", "https://github.com/blue13244/DogCareAI")
    for source in SOURCES.values():
        source_link(source)
