# 문헌 증상 비교

수의학 출처에서 선택한 징후와 설문 응답을 대조합니다. 모델의 학습 라벨·거리·투표값은 비교 개수에 사용하지 않습니다. 아래는 각 자료의 일부 징후를 선택한 목록이며, 질환별 모든 증상을 망라한 체크리스트가 아닙니다.

## 계산

- `matched_count`: 해당 문헌 징후와 응답이 일치한 개수
- `assessed_count`: 현재 설문으로 대조할 수 있고 유효한 응답이 있는 개수
- `unassessed_count`: 설문 항목이 없거나 유효한 응답이 없는 개수
- `reference_count = assessed_count + unassessed_count`

예: 물·배뇨 증가, 식사 변화 없음 → C01은 3개 비교 중 2개 일치, 미확인 1개(체중 감소). 소형견이거나 체중이 학습 평균보다 가볍다는 이유로 체중 감소·질환 징후를 추가하지 않습니다.

생활 변화 1·2는 감소, 4·5는 증가로 대조하고 3은 해당 방향의 변화가 보고되지 않은 응답입니다. 이진 증상은 1이면 일치, 0이면 없음으로 응답한 항목입니다. 누락·유효하지 않은 값은 미확인으로 남깁니다. 설문을 제출할 때 선택하지 않은 긴급 징후는 미선택 응답이며 CSV에는 해당 확인 자체가 없으므로 미확인입니다.

일치 수를 퍼센트로 환산하거나 순위로 정렬하지 않습니다. 여러 질환에서 같은 징후가 나타날 수 있고, 일치하지 않아도 질환을 배제하지 않습니다. 결과는 진단이나 진료 우선순위가 아닙니다. 긴급 안내는 별도 규칙을 유지합니다.

## 선택한 문헌 항목

| ID | 참고 항목 | 설문으로 대조하는 징후 | 현재 미확인으로 남기는 징후 | 출처 |
|---|---|---|---|---|
| C01 | 당뇨병 | 음수·배뇨·식사 증가 | 시간에 따른 체중 감소 | [Merck](https://www.merckvetmanual.com/endocrine-system/the-pancreas/diabetes-mellitus-in-dogs-and-cats) |
| C02 | 만성 신장 질환 | 음수·배뇨 증가, 식사 감소, 구토 | 선택한 4개 항목은 설문에서 확인 | [VCA](https://vcahospitals.com/parkcrest/know-your-pet/kidney-failure-chronic-in-dogs) |
| C03 | 위장관·식이성 문제 | 구토·설사, 식사·활동 감소 | 선택한 4개 항목은 설문에서 확인 | [VCA](https://vcahospitals.com/fleming-island/know-your-pet/gastroenteritis-in-dogs) |
| C04 | 위장관 이물·폐색 | 구토·설사, 식사 감소 | 복통·탈수 | [Cornell](https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-topics/gastrointestinal-foreign-body-obstruction-dogs) |
| C05 | 호흡기 질환 | 기침·호흡곤란 | 코 분비물 | [Cornell](https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-topics/canine-respiratory-disease-outbreaks) |
| C06 | 기관 허탈 | 기침·호흡곤란 | 거위 울음 같은 마른 기침 | [Cornell](https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-topics/tracheal-collapse) |
| C07 | 골관절염 | 보행 이상·활동 감소 | 일어날 때 뻣뻣함, 계단·점프 어려움 | [Cornell](https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-topics/osteoarthritis) |
| C08 | 위확장·염전 긴급 징후 | 복부팽창과 헛구역질의 복합 응답, 실신·의식저하 | 침 흘림·복통 | [ACVS](https://www.acvs.org/small-animal/gastric-dilatation-volvulus/) |
| C09 | 쿠싱증후군 | 음수·배뇨·식사 증가 | 탈모·배가 불러 보임·헐떡거림 | [Merck](https://www.merckvetmanual.com/endocrine-system/the-adrenal-glands/cushing-syndrome-hyperadrenocorticism-in-animals) |
| C10 | 췌장염 | 구토·설사, 식사 감소 | 복통·탈수 | [Merck](https://www.merckvetmanual.com/digestive-system/the-exocrine-pancreas/pancreatitis-in-dogs-and-cats) |
| C11 | 감염성 호흡기 질환 | 기침·호흡곤란, 식사 감소 | 재채기·코 분비물·발열 | [Cornell](https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-information/bordetellosis) |
| C12 | 슬개골 탈구 | 포괄적인 보행 이상 | 잠깐 다리를 드는 양상·관절 통증 | [ACVS](https://www.acvs.org/small-animal/patellar-luxations/) |

설문값이 누락되면 위 표에서 비교 가능한 징후도 미확인이 됩니다. CSV의 C05·C06·C08·C11은 긴급 징후가 미확인인 만큼 비교 개수가 줄어듭니다. C08의 복합 체크박스는 한 개로 계산하며 다른 항목으로 중복 계산하지 않습니다. C06의 일반 기침 응답으로 특정 기침 소리를 확인하지 않습니다. C09의 헐떡거림을 호흡곤란과 같은 항목으로 취급하지 않습니다. C12의 일반 보행 이상만으로 특정 보행 양상이나 통증을 확인하지 않습니다.

## 자료 관리와 범위

현재 화면·CSV는 `data/symptom_profiles.json`과 `symptom_compare.py`를 사용합니다. `data/condition_guide.csv`와 `health_guide.related_conditions`는 이전 연결 규칙의 호환용이며 현재 비교 개수나 출처 화면에 사용하지 않습니다. 프로필 변경 시 출처 원문과 대응 문구를 확인하고 테스트를 실행해야 합니다. 수의사 임상 검토와 실제 환자에 대한 성능 검증은 아직 수행하지 않았습니다.

