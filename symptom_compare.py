"""문헌 비교 항목과 응답의 일치·미확인을 구분한다. 항목 수만 반환한다."""
from __future__ import annotations
import json
import math
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parent / "data/symptom_profiles.json"


def load_profiles(path=PROFILE_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    symptoms, profiles = data["symptoms"], data["profiles"]
    ids = [p["condition_id"] for p in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError("증상 비교 자료의 질환 ID가 중복되었습니다.")
    allowed = {"increased", "decreased", "present", "flag", "unassessed"}
    for key, item in symptoms.items():
        if item.get("op") not in allowed or not item.get("label"):
            raise ValueError(f"잘못된 비교 항목: {key}")
    for profile in profiles:
        keys = profile["symptoms"]
        if not keys or len(keys) != len(set(keys)) or any(k not in symptoms for k in keys):
            raise ValueError("질환의 비교 항목이 없거나 중복·미등록 항목이 있습니다.")
        if not profile.get("source_url", "").startswith("https://"):
            raise ValueError("증상 비교 자료에 출처가 없습니다.")
    return data


def observe(item, record, red_flags=None):
    op = item["op"]
    if op == "unassessed":
        return "unknown", "현재 설문으로 확인하지 않음"
    if op == "flag":
        if red_flags is None:
            return "unknown", "긴급 징후 응답 없음"
        present = item["flag"] in red_flags
        return ("matched", "선택함") if present else ("not_reported", "선택하지 않음")
    value = record.get(item["field"])
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown", "응답 없음 또는 비교 불가"
    if not math.isfinite(number):
        return "unknown", "응답 없음 또는 비교 불가"
    if op == "present":
        if number not in (0, 1):
            return "unknown", "응답 형식이 맞지 않음"
        return ("matched", "있음") if number == 1 else ("not_reported", "없음으로 응답")
    if not number.is_integer() or not 1 <= number <= 5:
        return "unknown", "응답 형식이 맞지 않음"
    scales = {1:"많이 감소",2:"조금 감소",3:"평소와 같음",4:"조금 증가",5:"많이 증가"}
    matched = number > 3 if op == "increased" else number < 3
    return ("matched" if matched else "not_reported"), f"{int(number)} · {scales[int(number)]}"


def compare_symptoms(record, red_flags=None, profiles_path=PROFILE_PATH):
    if red_flags is not None and not isinstance(red_flags, (list, tuple, set)):
        raise ValueError("긴급 징후는 선택 항목 목록이어야 합니다.")
    data = load_profiles(profiles_path)
    results = []
    for profile in data["profiles"]:
        evidence = []
        for key in profile["symptoms"]:
            item = data["symptoms"][key]
            status, answer = observe(item, record, red_flags)
            evidence.append({"key":key, "label":item["label"], "status":status, "answer":answer})
        matched = [e["label"] for e in evidence if e["status"] == "matched"]
        unknown = [e["label"] for e in evidence if e["status"] == "unknown"]
        assessed = len(evidence) - len(unknown)
        results.append({"condition_id":profile["condition_id"], "name":profile["name"],
            "matched_count":len(matched), "assessed_count":assessed, "unassessed_count":len(unknown),
            "reference_count":len(evidence), "matched_signs":matched, "unassessed_signs":unknown,
            "evidence":evidence, "note":profile["note"], "source_name":profile["source_name"],
            "source_url":profile["source_url"]})
    # 문헌 목록 순서를 유지한다. 서로 다른 비교 항목 수로 진료 우선순위를 정하지 않는다.
    return results


def comparison_summary(results):
    return "; ".join(f"{r['name']}: 비교 {r['assessed_count']}개 중 {r['matched_count']}개 일치, 미확인 {r['unassessed_count']}개"
                     for r in results if r["matched_count"] > 0) or "비교 가능한 항목에서 일치 징후 없음"

