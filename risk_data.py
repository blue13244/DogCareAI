"""실제 발병 자료의 구조 점검. 확률 모델이나 임상 검증을 대신하지 않는다."""
from __future__ import annotations

import csv
import io
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

PREDICTORS = ["나이_세", "체중_kg", "식사량", "음수량", "배뇨량", "활동량", "수면시간",
              "증상_구토", "증상_설사", "증상_기침", "증상_보행이상", "크기", "약물복용"]
OUTCOME_FIELDS = ["개체ID", "기준일", "질환코드", "기준일질환없음확인", "추적종료일",
                  "발병여부", "확진일", "확인근거", "자료출처", "데이터구분"]
TEMPLATE_FIELDS = OUTCOME_FIELDS + PREDICTORS
SYNTHETIC_KINDS = {"가상_데모", "합성", "synthetic", "교육용 합성 데이터"}


def load_rows(source):
    if hasattr(source, "getvalue"):
        raw = source.getvalue()
    elif isinstance(source, bytes):
        raw = source
    else:
        raw = Path(source).read_bytes()
    for encoding in ["utf-8-sig", "cp949"]:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        reader = csv.DictReader(io.StringIO(text))
        fields = [str(c).strip() for c in (reader.fieldnames or [])]
        if not fields or len(fields) != len(set(fields)):
            raise ValueError("CSV에 열 이름이 없거나 중복되었습니다.")
        reader.fieldnames = fields
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("CSV 행의 값 개수가 열 이름 개수와 다릅니다.")
            rows.append({k: str(v or "").strip() for k, v in row.items()})
        return fields, rows
    raise ValueError("UTF-8 또는 CP949 CSV를 사용해 주세요.")


def template_bytes():
    output = io.StringIO(newline="")
    csv.writer(output).writerow(TEMPLATE_FIELDS)
    return output.getvalue().encode("utf-8-sig")


def validate_predictors(row):
    for field in PREDICTORS:
        value = row.get(field, "")
        if field == "크기":
            if value not in {"소형견", "중형견", "대형견"}:
                raise ValueError("크기는 소형견·중형견·대형견 중 하나여야 합니다.")
        elif field == "약물복용":
            if value not in {"O", "X"}:
                raise ValueError("약물복용은 영문 O 또는 X여야 합니다.")
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{field}가 비어 있거나 숫자가 아닙니다.") from None
            if not math.isfinite(number):
                raise ValueError(f"{field}는 유한한 숫자여야 합니다.")
            if field.startswith("증상_"):
                valid = number in (0, 1)
            elif field == "나이_세":
                valid = 0 <= number <= 35
            elif field == "체중_kg":
                valid = 0 < number <= 150
            else:
                valid = number.is_integer() and 1 <= number <= 5
            if not valid:
                raise ValueError(f"{field}가 입력 범위를 벗어났습니다.")


def outcome_for_horizon(row, horizon_days):
    """실제 기록에서 기간 내 발병/미발병/추적 부족을 구분한다. 발병 정답을 추측하지 않는다."""
    if horizon_days <= 0:
        raise ValueError("예측 기간은 1일 이상이어야 합니다.")
    if row.get("데이터구분") != "실제_관찰":
        raise ValueError("실제 관찰로 출처가 확인된 자료만 발병 자료로 점검합니다.")
    for field in ["개체ID", "질환코드", "확인근거", "자료출처"]:
        if not row.get(field):
            raise ValueError(f"{field}가 필요합니다.")
    if row.get("기준일질환없음확인") not in {"0", "1"}:
        raise ValueError("기준일질환없음확인은 확인된 0 또는 1을 입력해야 합니다.")
    if row["기준일질환없음확인"] == "0":
        return {"status": "baseline_excluded", "target": None}
    if row.get("발병여부") not in {"0", "1"}:
        raise ValueError("발병여부는 실제 확인 결과인 0 또는 1을 입력해야 합니다.")
    try:
        baseline = date.fromisoformat(row["기준일"])
        followup = date.fromisoformat(row["추적종료일"])
    except (KeyError, ValueError):
        raise ValueError("기준일·추적종료일은 YYYY-MM-DD 형식이어야 합니다.") from None
    if followup < baseline:
        raise ValueError("추적종료일은 기준일보다 빠를 수 없습니다.")
    cutoff = baseline + timedelta(days=horizon_days)
    if row["발병여부"] == "1":
        try:
            event = date.fromisoformat(row.get("확진일", ""))
        except ValueError:
            raise ValueError("발병 기록에는 실제 확진일이 필요합니다.") from None
        if not baseline < event <= followup:
            raise ValueError("확진일은 기준일 뒤이며 추적종료일까지여야 합니다.")
        if event <= cutoff:
            return {"status": "observed_event", "target": 1}
    elif row.get("확진일"):
        raise ValueError("미발병 기록에 확진일이 있습니다. 기록을 확인해 주세요.")
    if followup >= cutoff:
        return {"status": "observed_no_event", "target": 0}
    return {"status": "censored", "target": None}


def audit_csv(source, horizon_days=90):
    if not isinstance(horizon_days, int) or horizon_days <= 0:
        raise ValueError("점검 기간은 1일 이상의 정수여야 합니다.")
    fields, rows = load_rows(source)
    original_column_count = len(fields)
    if "개체ID" not in fields and "ID" in fields:
        fields = fields + ["개체ID"]
        rows = [{**row, "개체ID": row["ID"]} for row in rows]
    missing = [field for field in TEMPLATE_FIELDS if field not in fields]
    kinds = Counter(row.get("데이터구분", "미기록") for row in rows)
    counts = Counter()
    errors = []
    seen = set()
    if not missing:
        for index, row in enumerate(rows, 2):
            key = (row.get("개체ID"), row.get("기준일"), row.get("질환코드"))
            try:
                if key in seen:
                    raise ValueError("동일 개체·기준일·질환코드의 기록이 중복되었습니다.")
                seen.add(key)
                validate_predictors(row)
                result = outcome_for_horizon(row, horizon_days)
                counts[result["status"]] += 1
            except ValueError as exc:
                counts["invalid"] += 1
                if len(errors) < 20:
                    errors.append({"CSV행": index, "문제": str(exc)})
    return {"rows": len(rows), "columns": original_column_count, "missing_fields": missing,
            "synthetic_rows": sum(n for kind, n in kinds.items() if kind in SYNTHETIC_KINDS),
            "real_marked_rows": kinds.get("실제_관찰", 0), "horizon_days": horizon_days,
            "outcome_counts": dict(counts), "errors": errors,
            "probability_available": False,
            "model_status": "질환별 발병 모델·확률 보정·외부 검증이 등록되지 않았습니다.",
            "scope": "CSV 형식과 기록 시점의 구조 점검입니다. 출처의 진위나 임상적 타당성을 검증한 결과가 아닙니다."}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="DogCareAI 실제 발병 자료 구조 점검")
    parser.add_argument("--data", default=str(Path(__file__).resolve().parent / "data/dog_data.csv"))
    parser.add_argument("--horizon-days", type=int, default=90)
    args = parser.parse_args()
    try:
        report = audit_csv(args.data, args.horizon_days)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"자료 점검 실패: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))

