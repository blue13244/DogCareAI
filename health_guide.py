"""출처가 있는 건강 참고정보. ML 분류 결과로 진료 안내를 낮추지 않는다."""
from pathlib import Path
import csv

GUIDE_PATH = Path(__file__).resolve().parent / "data" / "condition_guide.csv"
SOURCES = {
    "triage": ("Merck Veterinary Manual: When to See a Veterinarian", "https://www.merckvetmanual.com/multimedia/table/when-to-see-a-veterinarian"),
    "age": ("AAHA: Canine Life Stage Definitions", "https://www.aaha.org/resources/life-stage-canine-2019/canine-life-stage-definitions/"),
    "weight": ("AAHA: Nutritional Screening Evaluation", "https://www.aaha.org/resources/2021-aaha-nutrition-and-weight-management-guidelines/screening-evaluation/"),
    "airway": ("Merck: Respiratory Diseases of Dogs and Cats", "https://www.merckvetmanual.com/respiratory-system/respiratory-diseases-of-small-animals/overview-of-respiratory-diseases-of-dogs-and-cats"),
    "gdv": ("ACVS: Gastric Dilatation-Volvulus", "https://www.acvs.org/small-animal/gastric-dilatation-volvulus/"),
}
RED_FLAGS = ["호흡곤란", "실신·의식저하", "소변을 보려 해도 나오지 않음", "복부팽창과 토하지 못하는 헛구역질", "경련", "심한 통증·출혈"]


def triage(record: dict, red_flags=None, duration_hours=0, persistent_cough=False):
    flags = list(red_flags or [])
    if any(f not in RED_FLAGS for f in flags):
        raise ValueError("알 수 없는 긴급 증상입니다.")
    if flags:
        return {"level": "urgent", "title": "지금 동물병원에 연락하고 즉시 진료를 받으세요.",
                "reason": "선택한 증상: " + ", ".join(flags), "source": SOURCES["triage"]}
    reasons = []
    if duration_hours >= 24 and (record.get("증상_구토", 0) or record.get("증상_설사", 0)):
        reasons.append("구토 또는 설사가 24시간 이상 지속됨")
    if persistent_cough:
        reasons.append("지속되는 기침")
    if record["음수량"] == 5:
        reasons.append("평소보다 물을 많이 마신다고 응답함")
    if duration_hours >= 24 and record.get("증상_보행이상", 0):
        reasons.append("보행 이상이 24시간 이상 지속됨")
    if reasons:
        return {"level": "soon", "title": "가급적 24시간 이내 진료를 상담하세요.",
                "reason": ", ".join(reasons) + ". 악화하거나 긴급 증상이 생기면 즉시 진료를 받으세요.", "source": SOURCES["triage"]}
    return {"level": "record", "title": "변화의 시작 시점과 지속 여부를 기록하세요.",
            "reason": "이 화면에 긴급 안내가 없더라도 안전하다는 뜻은 아닙니다. 증상이 지속·악화되거나 걱정되면 동물병원에 상담하세요.", "source": SOURCES["triage"]}


def related_conditions(record: dict, red_flags=None, guide_path=GUIDE_PATH):
    flags = set(red_flags or [])
    triggers = {
        "water_urine": record["음수량"] >= 4 and record["배뇨량"] >= 4,
        "digestive": bool(record["증상_구토"] or record["증상_설사"]),
        "foreign_body": bool(record["증상_구토"] and record["식사량"] <= 2),
        "cough": bool(record["증상_기침"]),
        "small_cough": record["크기"] == "소형견" and bool(record["증상_기침"]),
        "gait": bool(record["증상_보행이상"]),
        "gdv_signs": "복부팽창과 토하지 못하는 헛구역질" in flags,
        "cushing_signs": record["음수량"] >= 4 and record["배뇨량"] >= 4 and record["식사량"] >= 4,
        "vomiting_appetite": bool(record["증상_구토"]) and record["식사량"] <= 2,
        "small_gait": record["크기"] == "소형견" and bool(record["증상_보행이상"]),
    }
    required = {"condition_id", "참고질환", "trigger", "연결이유", "확인정보", "출처명", "출처URL"}
    with Path(guide_path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        guide = list(reader)
    if not required.issubset(columns) or any(row.get("trigger") not in triggers for row in guide):
        raise ValueError("condition_guide.csv의 열 또는 조건 이름이 올바르지 않습니다.")
    # CSV 조건은 고정된 키로만 해석한다. eval이나 사용자 코드 실행을 사용하지 않는다.
    return [row for row in guide if triggers[row["trigger"]]]


def size_guidance(size):
    if size == "소형견":
        return ("소형견의 기침은 기관·기도 문제 등 여러 원인과 관련될 수 있습니다. 기침 형태와 발생 상황을 기록해 상담하세요. 크기만으로 원인을 정할 수 없습니다.", SOURCES["airway"])
    if size == "대형견":
        return ("크고 가슴이 깊은 견종은 위확장·염전 위험요인과 관련됩니다. 복부가 부풀고 토하지 못하는 헛구역질이 함께 있으면 즉시 진료가 필요합니다. 다른 크기의 개에서도 발생할 수 있습니다.", SOURCES["gdv"])
    return ("크기 구분은 넓은 범주입니다. 체중·근육 상태·활동 수준과 개별 견종 특성을 함께 살펴야 합니다.", SOURCES["weight"])


def age_guidance(age, size):
    if age < 1:
        text = "성장기의 영양·예방접종·행동 발달을 상담하세요. 성장과 성숙 시기는 견종과 크기에 따라 달라집니다."
    else:
        text = "나이에 맞춘 예방관리와 생활 변화를 정기적으로 상담하세요. 노령 단계는 나이 하나로 정해지지 않으며 체구·견종·개별 상태를 함께 고려합니다."
    return f"입력 나이 {age:g}세, {size}. {text}", SOURCES["age"]


def daily_care(record):
    texts = ["식사·음수·배뇨·활동·수면 변화와 추가 증상의 시작 시점, 빈도, 지속 시간을 기록하세요."]
    if record["약물복용"] == "O":
        texts.append("상담 시 복용 중인 약 이름과 복용 시점을 함께 전달하세요. 앱 결과로 처방약을 중단하거나 용량을 바꾸지 마세요.")
    texts.append("체중은 같은 강아지의 이전 기록과 비교하고, 적정 체중은 체형 점수와 근육 상태를 포함해 상담하세요.")
    return texts

