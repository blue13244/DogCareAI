"""Streamlit Community Cloud 진입점: app.py"""
import json

import pandas as pd
import streamlit as st

from core import (MODEL_PATH, SCORES, SYMPTOMS, LABELS, FEATURES,
                  get_bundle, file_digest, analyze_record, batch_analyze, read_data)
from health_guide import (RED_FLAGS, SOURCES, triage,
                          size_guidance, age_guidance, daily_care)
from symptom_compare import load_profiles, compare_symptoms, comparison_summary


def presentation_text(value):
    """학습 파일의 원래 스키마를 유지하면서 화면 용어만 정리한다."""
    text = str(value)
    for original, display in [
        ("가상_데모", "교육용 합성 데이터"),
        ("가상건강상태라벨", "학습라벨"),
        ("가상라벨", "분류라벨"),
        ("가상 자료", "합성 데이터"),
        ("가상 라벨", "학습 라벨"),
        ("가상 사례", "사례"),
    ]:
        text = text.replace(original, display)
    return text


def presentation_frame(frame):
    data = frame.copy()
    data = data.rename(columns={c: presentation_text(c) for c in data.columns})
    for column in ["데이터구분", "학습자료구분"]:
        if column in data:
            data[column] = data[column].map(presentation_text)
    return data


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
    st.error(f"모델 준비에 실패했습니다: {presentation_text(exc)}")
    st.info("저장소의 requirements.txt와 data/dog_data.csv를 확인하고 python train.py로 다시 학습해 주세요.")
    st.stop()

with st.sidebar:
    st.markdown("### DogCare AI")
    page = st.radio("메뉴", ["강아지 상태 설문", "CSV 일괄 분석", "증상 비교 자료", "모델·데이터", "사용 안내"], label_visibility="collapsed")
    st.divider()
    st.caption(f"학습 자료 {len(bundle['records'])}건")
    st.caption("생활 패턴과 비슷한 사례를 확인하는 교육용 프로젝트입니다.")
    st.link_button("GitHub 프로젝트", "https://github.com/blue13244/DogCareAI")

st.html('<div class="brand-kicker">DOGCARE AI / EVERYDAY OBSERVATIONS</div>')
st.title("작은 변화를 기록하고,\n생활 패턴을 살펴보세요.")
st.html('<div class="hero-copy">평소와 비교한 설문으로 생활 패턴과 유사 사례를 확인합니다. 관련 증상 비교에서는 문헌과 일치한 징후, 미확인 항목과 출처를 함께 살펴봅니다.</div>')
st.caption("생활 패턴 모델은 교육용 합성 데이터 100건으로 학습했습니다. 증상 비교는 수의학 문헌의 선택 항목과 응답을 대조합니다. 참고용이며 수의사의 진단을 대신하지 않습니다.")


def source_link(source):
    st.markdown(f"[참고: {source[0]}]({source[1]})")


# 코드 업데이트 전 세션에 남은 결과는 새 설문을 통해 갱신한다.
if "analysis" in st.session_state and "comparisons" not in st.session_state.analysis:
    del st.session_state.analysis


def render_comparisons(comparisons, key):
    st.caption("일치 수 / 비교 가능한 항목 수와 미확인 수를 표시합니다. 문헌의 모든 증상을 망라하지 않으며, 일치 수는 질환 순위·중증도·진료 우선순위를 뜻하지 않습니다.")
    show_all = st.checkbox("일치 항목이 없는 문헌도 보기", key=key)
    visible = [r for r in comparisons if show_all or r["matched_count"] > 0]
    if not visible:
        st.info("비교 가능한 항목에서 일치 징후가 없습니다. 질환이 없다는 의미는 아닙니다.")
        return
    st.dataframe(pd.DataFrame([{"ID": r["condition_id"], "관련 문헌 항목": r["name"],
        "일치 수": r["matched_count"], "비교 가능한 수": r["assessed_count"],
        "미확인 수": r["unassessed_count"]} for r in visible]), hide_index=True, width="stretch")
    status_labels = {"matched": "일치", "not_reported": "해당 징후 응답 없음", "unknown": "미확인"}
    for item in visible:
        with st.expander(f"{item['name']} · {item['assessed_count']}개 비교 중 {item['matched_count']}개 일치 · 미확인 {item['unassessed_count']}개"):
            st.dataframe(pd.DataFrame([{"문헌의 선택 징후": e["label"], "설문 응답": e["answer"],
                "비교 결과": status_labels[e["status"]]} for e in item["evidence"]]), hide_index=True, width="stretch")
            st.write(item["note"])
            source_link((item["source_name"], item["source_url"]))
    st.caption("미확인은 증상이 없다는 뜻이 아닙니다. 여러 질환에 같은 징후가 겹칠 수 있으며, 일치하지 않아도 질환을 배제할 수 없습니다.")


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
    st.subheader(presentation_text(result["virtual_label_display"]))
    st.caption(f"학습 라벨: {result['virtual_label']}. 이 분류는 건강 정상 여부나 진료 필요성의 판단이 아닙니다.")
    a,b,c = st.columns(3)
    a.metric("학습된 생활 군집", result["pattern"]["name"])
    b.metric("같은 군집의 사례", f"{result['pattern']['rows']}건")
    c.metric("비교할 유사 사례", f"{len(result['neighbors'])}건")
    pattern_tab, similar_tab, health_tab, profile_tab = st.tabs(["생활 변화 패턴", "유사 사례 비교", "관련 증상 비교", "체중·나이·크기"])
    with pattern_tab:
        st.write("**이번 입력에서 보고한 변화**")
        for text in result["changes"]:
            st.write("• " + text)
        comparison = pd.DataFrame({"항목": SCORES * 2,
            "점수": [record[c] for c in SCORES] + [result["pattern"]["means"][c] for c in SCORES],
            "비교": ["내 응답"] * len(SCORES) + ["같은 군집 평균"] * len(SCORES)})
        st.vega_lite_chart(comparison, {
            "mark": "bar", "height": 320,
            "encoding": {
                "x": {"field": "점수", "type": "quantitative", "title": "응답 점수 (3=평소)", "scale": {"domain": [0, 5]}},
                "y": {"field": "항목", "type": "nominal", "sort": SCORES, "title": None},
                "yOffset": {"field": "비교", "type": "nominal"},
                "color": {"field": "비교", "type": "nominal", "legend": {"orient": "bottom", "title": None},
                          "scale": {"domain": ["내 응답", "같은 군집 평균"], "range": ["#246C59", "#A5BDB0"]}},
                "tooltip": [{"field": "항목"}, {"field": "비교"}, {"field": "점수", "format": ".2f"}],
            },
        }, width="stretch")
        st.caption("3은 평소와 같음입니다. 응답은 순서형 점수이며 양·시간의 실제 비율을 뜻하지 않습니다. 군집은 학습 자료에서 찾은 그룹입니다.")
    with similar_tab:
        st.write("학습된 입력 표현에서 가까운 사례를 보여 줍니다.")
        st.dataframe(presentation_frame(result["neighbors"]), hide_index=True, width="stretch")
        st.caption("모델거리는 작을수록 입력 특징이 가깝다는 뜻입니다. 나이·체중·크기·복용 여부·설문·추가 증상을 함께 비교합니다.")
    with health_tab:
        st.write("**설문 응답과 문헌 징후의 비교**")
        render_comparisons(saved["comparisons"], "result_show_all")
        st.write("**생활 관리와 상담 준비**")
        for text in daily_care(record):
            st.write("• " + text)
        source_link(SOURCES["weight"])
    with profile_tab:
        w = result["weight"]
        if w:
            st.subheader("같은 크기의 학습 자료와 체중 비교")
            a,b,c = st.columns(3)
            a.metric("입력 체중", f"{record['체중_kg']:.1f} kg")
            b.metric(f"{w['size']} {w['count']}건 평균", f"{w['mean_kg']:.1f} kg")
            c.metric("평균과의 차이", f"{w['difference_kg']:+.1f} kg")
            st.caption(presentation_text(w["scope"]))
            source_link(SOURCES["weight"])
        st.subheader("크기에 따른 참고정보")
        text, source = size_guidance(record["크기"])
        st.write(text); source_link(source)
        st.subheader("나이에 따른 관리정보")
        text, source = age_guidance(record["나이_세"], record["크기"])
        st.write(text); source_link(source)
        if record.get("견종"):
            st.caption("입력한 견종은 기록에 보존합니다. 학습 자료에 견종 열이 없어 견종별 위험도 계산에는 사용하지 않습니다.")
    export = {**record, "AI분류라벨": result["virtual_label"], "생활패턴": result["pattern"]["name"],
              "변화요약": ", ".join(result["changes"]), "진료안내": safety["title"],
              "증상비교요약": comparison_summary(saved["comparisons"]), "학습자료구분": "교육용 합성 데이터"}
    for item in saved["comparisons"]:
        for field, label in [("matched_count", "일치수"), ("assessed_count", "비교수"), ("unassessed_count", "미확인수")]:
            export[f"{item['condition_id']}_{label}"] = item[field]
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
                                       help="선택한 긴급 증상은 AI의 분류 결과와 별도로 우선 안내합니다.")
            duration = st.selectbox("추가 증상의 지속 시간", ["해당 없음 또는 모름", "24시간 미만", "24시간 이상"])
            persistent = st.checkbox("기침이 계속되거나 반복됨")
        submitted = st.form_submit_button("AI로 생활 변화 분석", type="primary", width="stretch")
    if submitted:
        record = {"이름": name, "견종": breed, "나이_세": age, "체중_kg": weight,
                  "크기": size, "약물복용": medicine, **values, **symptoms}
        try:
            result = analyze_record(record, bundle, red_flags=red_flags)
            safety = triage(record, red_flags, duration_hours=24 if duration=="24시간 이상" else 0, persistent_cough=persistent)
            st.session_state.analysis = {"record": record, "analysis": result, "safety": safety,
                                         "comparisons": result["symptom_comparisons"]}
        except (ValueError, OSError) as exc:
            st.error(presentation_text(exc))
    if "analysis" in st.session_state:
        render_result(st.session_state.analysis)

elif page == "CSV 일괄 분석":
    st.header("CSV 일괄 분석")
    st.write("학습에 사용한 것과 같은 13개 입력 열이 있는 CSV를 올리세요. 라벨과 ID가 없어도 분석할 수 있습니다.")
    st.caption("생활 패턴과 문헌 증상 비교를 함께 제공합니다. CSV에 없는 긴급 징후는 미확인으로 처리합니다. 개별 진료 안내는 설문에서 확인하세요.")
    uploaded = st.file_uploader("분석할 CSV", type=["csv"])
    if uploaded:
        try:
            data = read_data(uploaded)
            result = batch_analyze(data, bundle)
            st.dataframe(presentation_frame(result), hide_index=True, width="stretch")
            st.download_button("일괄 분석 CSV 내려받기", presentation_frame(result).to_csv(index=False).encode("utf-8-sig"), "DogCareAI_batch.csv", "text/csv")
            row_number = st.number_input("증상 비교 상세를 볼 행 (CSV 머리글 제외)", min_value=1, max_value=len(data), value=1, step=1)
            render_comparisons(compare_symptoms(data.iloc[int(row_number)-1]), "batch_show_all")
        except (ValueError, OSError, pd.errors.ParserError) as exc:
            st.error(presentation_text(exc))

elif page == "증상 비교 자료":
    st.header("증상 비교 자료")
    st.write("Merck Veterinary Manual, Cornell 수의과대학, ACVS, VCA의 자료에서 선택한 징후를 비교합니다. 아래 목록은 진단 순서가 아닌 고정된 자료 순서입니다.")
    if "analysis" in st.session_state:
        st.subheader("마지막 설문 응답과 비교")
        render_comparisons(st.session_state.analysis["comparisons"], "library_show_all")
    else:
        st.info("설문을 분석하면 이 화면에서도 일치·미확인 개수와 항목별 응답을 확인할 수 있습니다.")
    st.subheader("12개 문헌 항목과 출처")
    reference = load_profiles()
    for item in reference["profiles"]:
        with st.expander(f"{item['condition_id']} · {item['name']}"):
            st.write("비교에 사용하는 선택 징후: " + ", ".join(reference["symptoms"][key]["label"] for key in item["symptoms"]))
            st.write(item["note"])
            source_link((item["source_name"], item["source_url"]))

elif page == "모델·데이터":
    st.header("모델과 학습 데이터")
    m = bundle["metrics"]
    st.write(f"사용 중인 모델: {model_origin}")
    st.write("Random Forest 분류, K-Means 생활 군집, Nearest Neighbors 유사 사례 검색이 설문 결과에 실제로 사용됩니다.")
    st.info(presentation_text(m["interpretation"]))
    a,b,c = st.columns(3)
    a.metric("학습 기록", f"{m['rows']}건")
    b.metric("그룹 교차검증 정확도", f"{m['oof_accuracy']:.1%}")
    c.metric("Macro F1", f"{m['oof_macro_f1']:.3f}")
    st.caption(f"{m['cv_folds']}개 분할 · 최빈 라벨 기준선 {m['baseline_accuracy']:.1%}. 동일 ID 또는 동일 입력은 같은 그룹에 묶어 학습과 평가에 나뉘지 않게 했습니다.")
    st.write(m["deployment_model"])
    counts = pd.DataFrame({"학습 라벨": list(m["class_counts"]), "건수": list(m["class_counts"].values())})
    st.bar_chart(counts.set_index("학습 라벨"), color="#246C59")
    with st.expander("라벨별 성능과 혼동행렬"):
        report = {k:v for k,v in m["classification_report"].items() if isinstance(v,dict)}
        st.dataframe(pd.DataFrame(report).T)
        st.write("행: 정답 / 열: 예측")
        st.dataframe(pd.DataFrame(m["confusion_matrix"], index=LABELS, columns=LABELS))
    with st.expander("학습 변수와 제외한 정보"):
        st.write("학습 입력: " + ", ".join(FEATURES))
        st.write("제외: " + ", ".join(presentation_text(c) for c in m["excluded_columns"]))
        st.caption("정답을 설명하는 텍스트, 이름, ID를 분류기에 넣지 않습니다. ID는 평가 분할에만 사용합니다.")
    with st.expander("군집별 요약"):
        st.dataframe(pd.DataFrame([{k:v for k,v in p.items() if k!='means'} for p in bundle["profiles"]]), hide_index=True)
    with st.expander("학습 자료 확인"):
        st.dataframe(presentation_frame(bundle["records"].drop(columns=["이름"])), hide_index=True, width="stretch")
    st.download_button("모델 평가 JSON 내려받기", json.dumps(m, ensure_ascii=False, indent=2), "DogCareAI_metrics.json", "application/json")

else:
    st.header("사용 안내")
    st.markdown("""1. 강아지 기본 정보와 평소 대비 생활 변화를 입력합니다.
2. 추가 증상과 긴급 징후를 확인합니다.
3. 분석 버튼을 눌러 생활 군집, 사례 유형, 가까운 사례를 봅니다.
4. 관련 증상 비교에서 일치한 징후, 응답, 미확인 항목과 원문 출처를 확인합니다.

입력 내용은 파일이나 데이터베이스에 자동으로 저장하지 않습니다. 필요한 경우 결과 CSV를 직접 내려받을 수 있습니다.

**비교 결과 읽는 방법**

예를 들어 ‘3개 비교 중 2개 일치, 미확인 1개’는 문헌에서 선택한 4개 징후 중 설문으로 3개를 확인했고 그중 2개가 일치했다는 뜻입니다. 미확인은 증상이 없다는 뜻이 아닙니다. 문헌의 모든 증상을 포함하지 않으며, 일치 수로 질환의 우선순위나 중증도를 정하지 않습니다. 일치하지 않아도 질환을 배제할 수 없습니다.

생활 변화 1·2는 감소, 3은 평소와 같음, 4·5는 증가로 비교합니다. 단일 체중으로 체중 감소를 추정하지 않고, 수면시간·나이·크기·약물복용은 증상 일치 수에 더하지 않습니다. CSV에 없는 긴급 징후는 미확인으로 남깁니다. 진료 안내는 증상 일치 개수와 별도로 적용됩니다.
""")
    st.link_button("전체 코드와 배포 설명", "https://github.com/blue13244/DogCareAI")
    for source in SOURCES.values():
        source_link(source)

