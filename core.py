"""DogCareAI 데이터 검증, 학습, 생활 패턴 및 유사 사례 분석."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, silhouette_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from symptom_compare import compare_symptoms, comparison_summary

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "dog_data.csv"
MODEL_PATH = ROOT / "models" / "dog_model.joblib"
SCORES = ["식사량", "음수량", "배뇨량", "활동량", "수면시간"]
SYMPTOMS = ["증상_구토", "증상_설사", "증상_기침", "증상_보행이상"]
NUMERIC = ["나이_세", "체중_kg", *SCORES, *SYMPTOMS]
CATEGORICAL = ["크기", "약물복용"]
FEATURES = NUMERIC + CATEGORICAL
TARGET = "가상건강상태라벨"
LABELS = ["정상", "관찰 필요", "건강 이상 의심"]
LABEL_DISPLAY = {
    "정상": "변화가 적은 가상 사례 유형",
    "관찰 필요": "변화가 나타난 가상 사례 유형",
    "건강 이상 의심": "여러 변화·증상이 있는 가상 사례 유형",
}
SCHEMA_VERSION = "dogcare-demo-v1"


def file_digest(path=DATA_PATH) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_data(source=DATA_PATH, training=False) -> pd.DataFrame:
    raw = source.getvalue() if hasattr(source, "getvalue") else source if isinstance(source, bytes) else Path(source).read_bytes()
    for encoding in ["utf-8-sig", "cp949"]:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        header = next(csv.reader(io.StringIO(text)), [])
        clean_header = [c.strip().lstrip("\ufeff") for c in header]
        if len(set(clean_header)) != len(clean_header):
            raise ValueError("중복 열 이름이 있습니다.")
        frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
        return validate_data(frame, training=training)
    raise ValueError("CSV는 UTF-8 또는 CP949로 저장해 주세요.")


def validate_data(frame: pd.DataFrame, training=False) -> pd.DataFrame:
    data = frame.copy().reset_index(drop=True)
    data.columns = [str(c).strip().lstrip("\ufeff") for c in data.columns]
    if data.columns.duplicated().any():
        raise ValueError("중복 열 이름이 있습니다.")
    required = FEATURES + (["ID", TARGET, "데이터구분"] if training else [])
    missing = [c for c in required if c not in data]
    if missing:
        raise ValueError("필수 열 누락: " + ", ".join(missing))
    if data.empty:
        raise ValueError("CSV에 데이터 행이 없습니다.")
    for c in CATEGORICAL:
        data[c] = data[c].fillna("").astype(str).str.strip()
    data["약물복용"] = data["약물복용"].str.upper()
    if not data["크기"].isin(["소형견", "중형견", "대형견"]).all():
        raise ValueError("크기는 소형견·중형견·대형견 중 하나여야 합니다.")
    if not data["약물복용"].isin(["O", "X"]).all():
        raise ValueError("약물복용은 영문 O 또는 X여야 합니다.")
    for c in NUMERIC:
        numbers = pd.to_numeric(data[c], errors="coerce")
        bad = numbers.isna() | ~np.isfinite(numbers)
        if c in SCORES:
            bad |= ~numbers.between(1, 5) | (numbers % 1 != 0)
        elif c in SYMPTOMS:
            bad |= ~numbers.isin([0, 1])
        elif c == "나이_세":
            bad |= ~numbers.between(0, 35)
        else:
            bad |= (numbers <= 0) | (numbers > 150)
        if bad.any():
            rows = ", ".join(str(i+2) for i in data.index[bad][:6])
            raise ValueError(f"{c}: CSV {rows}행 값이 비어 있거나 허용 범위를 벗어났습니다.")
        data[c] = numbers.astype(int) if c in SCORES + SYMPTOMS else numbers.astype(float)
    if training:
        for c in ["ID", TARGET, "데이터구분"]:
            data[c] = data[c].fillna("").astype(str).str.strip()
            if data[c].eq("").any():
                raise ValueError(f"학습 자료의 {c}에 빈칸이 있습니다.")
        if not data[TARGET].isin(LABELS).all():
            raise ValueError("가상건강상태라벨은 정상·관찰 필요·건강 이상 의심 중 하나여야 합니다.")
        if not data["데이터구분"].eq("가상_데모").all():
            raise ValueError("현재 모델은 가상_데모 라벨 학습용입니다. 실제 관찰·확진 데이터는 별도 학습 목표와 검증을 설계해야 합니다.")
        # 같은 ID가 반복될 수 있지만, 다른 강아지의 기록에 같은 ID를 사용하면 안 된다.
    return data


def make_preprocessor():
    return ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ], remainder="drop", sparse_threshold=0)


def split_groups(data: pd.DataFrame) -> np.ndarray:
    """같은 ID 또는 완전히 같은 학습 입력을 가진 기록을 하나의 그룹으로 묶는다."""
    parent = list(range(len(data)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i, j):
        parent[find(i)] = find(j)
    seen_ids, seen_features = {}, {}
    for i, row in data.iterrows():
        key = tuple(row[c] for c in FEATURES)
        dog_id = str(row["ID"])
        if dog_id in seen_ids:
            union(i, seen_ids[dog_id])
        if key in seen_features:
            union(i, seen_features[key])
        seen_ids[dog_id], seen_features[key] = i, i
    return np.array([find(i) for i in range(len(data))])


def train_bundle(data: pd.DataFrame, data_sha256: str | None = None):
    data = validate_data(data, training=True)
    if len(data) < 100:
        raise ValueError("이 프로젝트는 최소 100행의 학습 CSV를 요구합니다. 행 복제로 개수를 늘리지 마세요.")
    x, y = data[FEATURES], data[TARGET]
    groups = split_groups(data)
    group_counts = pd.DataFrame({"label": y, "group": groups}).groupby("label")["group"].nunique().reindex(LABELS, fill_value=0)
    folds = min(5, int(group_counts.min()))
    if folds < 2:
        raise ValueError("각 라벨에 최소 2개의 독립적인 개체·입력 그룹이 필요합니다.")
    estimator = Pipeline([
        ("prepare", make_preprocessor()),
        ("classifier", RandomForestClassifier(n_estimators=240, max_depth=7, min_samples_leaf=2,
                                              class_weight="balanced", random_state=42, n_jobs=1)),
    ])
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=42)
    predictions = pd.Series(index=data.index, dtype=object)
    baseline_predictions = pd.Series(index=data.index, dtype=object)
    fold_details = []
    for fold, (a, b) in enumerate(splitter.split(x, y, groups), 1):
        if set(groups[a]) & set(groups[b]):
            raise RuntimeError("학습/평가 그룹 중복이 발견되었습니다.")
        if set(y.iloc[a]) != set(LABELS):
            raise ValueError("일부 평가 분할의 학습 자료에 라벨이 빠집니다. 개체별 라벨 분포를 확인해 주세요.")
        fitted = clone(estimator).fit(x.iloc[a], y.iloc[a])
        predictions.iloc[b] = fitted.predict(x.iloc[b])
        dummy = DummyClassifier(strategy="most_frequent").fit(x.iloc[a], y.iloc[a])
        baseline_predictions.iloc[b] = dummy.predict(x.iloc[b])
        fold_details.append({"fold": fold, "train_rows": len(a), "test_rows": len(b), "overlapping_groups": 0})
    estimator.fit(x, y)
    embedding = make_preprocessor()
    transformed = embedding.fit_transform(x)
    cluster_count = min(4, len(np.unique(transformed, axis=0)))
    if cluster_count < 2:
        raise ValueError("서로 다른 생활 패턴이 부족해 군집 학습을 할 수 없습니다.")
    clusterer = KMeans(n_clusters=cluster_count, n_init=20, random_state=42).fit(transformed)
    neighbors = NearestNeighbors(metric="euclidean", algorithm="brute").fit(transformed)
    profiles = []
    for cluster_id in range(cluster_count):
        members = data.loc[clusterer.labels_ == cluster_id]
        averages = {c: round(float(members[c].mean()), 2) for c in SCORES + SYMPTOMS}
        directions = sorted(SCORES, key=lambda c: abs(averages[c]-3), reverse=True)[:2]
        summary = " · ".join(f"{c} 평균 {averages[c]:.1f}" for c in directions)
        profiles.append({"cluster": cluster_id, "name": f"패턴 {cluster_id+1}", "rows": len(members), "summary": summary, "means": averages})
    metrics = {
        "schema_version": SCHEMA_VERSION,
        "data_kind": "가상_데모",
        "target": TARGET,
        "rows": len(data), "unique_ids": int(data["ID"].nunique()),
        "unique_inputs": len(data[FEATURES].drop_duplicates()), "evaluation_groups": len(np.unique(groups)),
        "class_counts": {k: int(v) for k, v in y.value_counts().items()},
        "cv_folds": folds, "folds": fold_details,
        "oof_accuracy": float(accuracy_score(y, predictions)),
        "oof_macro_f1": float(f1_score(y, predictions, labels=LABELS, average="macro", zero_division=0)),
        "baseline_accuracy": float(accuracy_score(y, baseline_predictions)),
        "classification_report": classification_report(y, predictions, labels=LABELS, output_dict=True, zero_division=0),
        "confusion_matrix_labels": LABELS,
        "confusion_matrix": confusion_matrix(y, predictions, labels=LABELS).tolist(),
        "cluster_silhouette_training_only": float(silhouette_score(transformed, clusterer.labels_)),
        "feature_columns": FEATURES,
        "excluded_columns": ["ID", "이름", "추가증상", TARGET, "판단주요특징", "데이터구분"],
        "evaluated_at_kst": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
        "interpretation": "가상 라벨 재현에 대한 그룹 교차검증입니다. 실제 질병·건강·진료 필요성 예측의 정확도가 아닙니다.",
        "deployment_model": "교차검증 후 분류기·군집·검색 모델을 전체 자료로 학습했습니다. 표시 성능은 교차검증에서만 계산했습니다.",
    }
    return {"schema_version": SCHEMA_VERSION, "data_sha256": data_sha256,
            "sklearn_version": sklearn.__version__, "classifier": estimator,
            "embedding": embedding, "clusterer": clusterer, "neighbors": neighbors,
            "profiles": profiles, "records": data, "metrics": metrics}


def save_bundle(bundle, model_path=MODEL_PATH):
    path = Path(model_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path, compress=3)
    path.with_name("metrics.json").write_text(json.dumps(bundle["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")


def get_bundle(data_path=DATA_PATH, model_path=MODEL_PATH):
    """저장소에 포함된 신뢰하는 로컬 모델만 읽고, 환경·데이터가 바뀌면 재학습한다."""
    digest = file_digest(data_path)
    path = Path(model_path)
    if path.is_file():
        try:
            bundle = joblib.load(path)
            if (bundle["schema_version"] == SCHEMA_VERSION and bundle["data_sha256"] == digest
                    and bundle["sklearn_version"] == sklearn.__version__):
                return bundle, "저장된 학습 모델"
        except (ValueError, OSError, KeyError, AttributeError, EOFError, ImportError):
            pass
    bundle = train_bundle(read_data(data_path, training=True), digest)
    # Cloud의 파일 시스템에 의존하지 않도록 자동 재학습 모델은 메모리에만 보관한다.
    return bundle, "CSV에서 현재 환경으로 다시 학습한 모델"


def changes(record) -> list[str]:
    scale = {1: "많이 감소", 2: "조금 감소", 3: "평소와 같음", 4: "조금 증가", 5: "많이 증가"}
    texts = [f"{c} {scale[int(record[c])]}" for c in SCORES if int(record[c]) != 3]
    texts += [c.replace("증상_", "") for c in SYMPTOMS if int(record[c]) == 1]
    return texts or ["입력한 생활 항목에서 변화가 보고되지 않았습니다."]


def weight_comparison(record, records):
    same_size = records.loc[records["크기"] == record["크기"]]
    if same_size.empty:
        return None
    mean = float(same_size["체중_kg"].mean())
    return {"count": len(same_size), "mean_kg": mean, "median_kg": float(same_size["체중_kg"].median()),
            "difference_kg": float(record["체중_kg"])-mean, "size": record["크기"],
            "scope": "같은 크기의 가상 자료 평균입니다. 적정 체중·비만 판정 기준이 아닙니다."}


def analyze_record(record: dict, bundle, top_k=5, exclude_id=None, red_flags=None):
    frame = validate_data(pd.DataFrame([record]))
    row = frame.iloc[0]
    features = frame[FEATURES]
    predicted = str(bundle["classifier"].predict(features)[0])
    vector = bundle["embedding"].transform(features)
    cluster_id = int(bundle["clusterer"].predict(vector)[0])
    distances, indices = bundle["neighbors"].kneighbors(vector, n_neighbors=len(bundle["records"]))
    selected = []
    seen = set()
    # 같은 개체의 반복 기록이 검색 결과를 차지하지 않게 한다.
    for distance, i in zip(distances[0], indices[0]):
        match = bundle["records"].iloc[int(i)]
        dog_id = str(match["ID"])
        if dog_id == exclude_id or dog_id in seen:
            continue
        seen.add(dog_id)
        selected.append({"사례ID": dog_id, "크기": match["크기"], "나이_세": float(match["나이_세"]),
                         "체중_kg": float(match["체중_kg"]), **{c: int(match[c]) for c in SCORES + SYMPTOMS},
                         "가상라벨": match[TARGET], "모델거리": round(float(distance), 3)})
        if len(selected) >= top_k:
            break
    return {"virtual_label": predicted, "virtual_label_display": LABEL_DISPLAY[predicted],
            "pattern": bundle["profiles"][cluster_id], "changes": changes(row),
            "neighbors": pd.DataFrame(selected), "weight": weight_comparison(row, bundle["records"]),
            "symptom_comparisons": compare_symptoms(row, red_flags)}


def batch_analyze(frame, bundle):
    data = validate_data(frame)
    # 이전 버전에서 내려받은 결과를 올려도 폐지한 출력 열을 다시 내보내지 않는다.
    retired = [c for c in data.columns if ("질병" in c and "확률" in c) or c == "disease_probability"]
    result = data.drop(columns=retired).copy()
    result["AI가상라벨"] = bundle["classifier"].predict(data[FEATURES])
    clusters = bundle["clusterer"].predict(bundle["embedding"].transform(data[FEATURES]))
    result["생활패턴"] = [bundle["profiles"][int(i)]["name"] for i in clusters]
    result["변화요약"] = data.apply(lambda r: ", ".join(changes(r)), axis=1)
    comparisons = [compare_symptoms(row) for _, row in data.iterrows()]
    result["증상비교요약"] = [comparison_summary(items) for items in comparisons]
    for profile in comparisons[0]:
        cid = profile["condition_id"]
        for key, label in [("matched_count", "일치수"), ("assessed_count", "비교수"), ("unassessed_count", "미확인수")]:
            result[f"{cid}_{label}"] = [next(item[key] for item in items if item["condition_id"] == cid) for items in comparisons]
    return result

