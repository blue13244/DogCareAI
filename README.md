# DogCare AI

[공유 웹앱 열기](https://gwinweskgtxcbsz5nczny5.streamlit.app/) · [GitHub 저장소](https://github.com/blue13244/DogCareAI)

강아지 설문을 입력하면 **학습된 모델로 생활 군집과 가상 사례 유형을 분석하고 비슷한 사례를 찾는** Streamlit 프로젝트입니다. 건강 참고정보에는 입력과 연결한 이유, 원문 출처를 표시합니다.

현재 학습 자료는 사용자가 제공한 **가상 반려견 100건**입니다. 실제 질병이나 건강 정상 여부를 진단하지 않으며, 실제 질병 발생 확률을 제공하지 않습니다.

## 기능

| 요청 기능 | 구현 내용 |
|---|---|
| 강아지 상태 설문 | 이름·견종(기록용)·크기·나이·체중·복용 여부, 생활 점수 5개, 추가 증상 4개 |
| CSV 100건 이상 학습 | 제공 CSV 100건을 실제로 학습하고 모델 파일 포함. 같은 구조의 100행 이상 CSV로 재학습 가능 |
| 생활 변화 패턴 분석 | K-Means로 배운 4개 생활 군집에 새 설문을 배정하고 군집 평균과 비교 |
| AI 가상 사례 분류 | Random Forest가 제공된 가상 상태 라벨을 예측 |
| 유사 사례 비교 | 학습한 전처리 공간에서 Nearest Neighbors로 가까운 서로 다른 개체 5건 검색 |
| 관련 질환 후보 안내 | 관찰 징후에 연결한 문헌 참고정보. 질환 예측 순위나 확률 아님 |
| 소·중·대형견 특성 | 크기를 모델 입력에 반영하고 크기별 참고정보 제공. 임의 임상 위험 가중치 없음 |
| 평균 체중 비교 | 같은 크기의 CSV 평균·중앙값 및 입력 체중과의 차이. 적정 체중 판단 아님 |
| 나이별 관리 정보 | 나이를 학습에 사용하고 성장·성숙·예방관리의 참고정보 제공 |
| 생활 관리·진료 안내 | 긴급 징후 우선 안내, 증상 지속 여부 확인, 상담 준비 정보 |
| 실제 질병 발생 확률 | **현재 자료로 산출 불가. 숫자를 만들어 표시하지 않음** |
| 실제 발병 자료 준비 | 진단·추적 CSV 양식, 30·90·180·365일 기간별 기록 구조·누락 점검 |

## 프로젝트 구조

```text
DogCareAI/
├── app.py
├── train.py
├── core.py
├── health_guide.py
├── risk_data.py             # 발병 자료 구조와 추적 기간 점검
├── data/
│   ├── dog_data.csv
│   ├── condition_guide.csv
│   └── clinical_outcomes_template.csv
├── models/
│   ├── dog_model.joblib
│   └── metrics.json
├── tests/
│   ├── test_dogcare.py
│   └── test_app.py
├── .streamlit/config.toml
├── requirements.txt
├── MODEL_CARD.md
├── CLINICAL_DATA.md
└── README.md
```

## 로컬 실행

Python 3.12 기준입니다. VS Code에서 이 저장소 폴더를 연 뒤 터미널에서 실행하세요.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS·Linux에서는 가상환경 Python 경로를 `.venv/bin/python`으로 바꿉니다.

저장 모델을 자동으로 불러옵니다. CSV 해시·모델 스키마·scikit-learn 버전이 맞지 않거나 모델이 없으면 같은 CSV로 메모리에서 다시 학습합니다. 공개 웹앱에서는 방문자의 업로드로 공용 학습 모델을 바꾸지 않습니다. 개인 ID 입력란도 없습니다.

## GitHub와 Streamlit Community Cloud 배포

이 프로젝트는 [blue13244/DogCareAI](https://github.com/blue13244/DogCareAI)의 루트에 배치합니다. 별도 프런트엔드 빌드나 API 키는 필요하지 않습니다. GitHub Pages는 Python 서버 실행용이 아니므로 Community Cloud를 사용합니다.

1. [Streamlit Community Cloud](https://share.streamlit.io/)에 GitHub 계정으로 로그인합니다.
2. **Create app**에서 GitHub 저장소로 배포하는 옵션을 선택합니다.
3. Repository: `blue13244/DogCareAI`
4. Branch: `main`
5. Main file path: `app.py`
6. Advanced settings의 Python을 **3.12**로 설정하고 배포합니다.
7. 배포가 완료되면 Streamlit이 발급한 실제 `*.streamlit.app` 주소를 공유합니다.

저장소 변경 사항은 Cloud에서 다시 반영됩니다. CSV를 바꾼 경우 `python train.py`로 모델을 재학습해 모델·평가 결과도 함께 커밋하는 것을 권장합니다. 배포 중 패키지 설치 오류가 나면 Cloud 로그에서 Python 버전과 requirements 설치 결과를 확인하세요.

[공식 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## 학습 자료와 입력 의미

`data/dog_data.csv`는 사용자가 제공한 `DogCareAI_반려견_학습데이터.csv`를 **수정하지 않고 복사한 파일**입니다. 원본의 19개 열과 `가상_데모` 표시를 보존했습니다.

- 100행, 100개 ID, 서로 다른 모델 입력 100개
- 라벨: 정상 38건, 관찰 필요 31건, 건강 이상 의심 31건
- 입력 누락 없음
- 확진명·확진 일자·기준 시점·추적 기간·신규 질병 발생 결과 없음

학습 입력 13개:

```text
나이_세, 체중_kg, 식사량, 음수량, 배뇨량, 활동량, 수면시간,
증상_구토, 증상_설사, 증상_기침, 증상_보행이상, 크기, 약물복용
```

생활 점수는 1 많이 감소, 2 조금 감소, 3 평소와 같음, 4 조금 증가, 5 많이 증가입니다. 각 강아지의 평소와 같은 관찰 기간을 기준으로 비교합니다. 순서형 응답이며 실제 양의 배수나 비율을 뜻하지 않습니다. 추가 증상은 0 없음, 1 있음입니다. 크기는 소형견·중형견·대형견, 복용 여부는 영문 O·X입니다.

빈칸이나 범위를 벗어난 설문은 임의로 3으로 바꾸지 않고 오류로 표시합니다. 화면의 나이 0~35세와 체중 0 초과~150kg은 입력 오류를 막기 위한 소프트웨어 범위이며 정상·안전 범위가 아닙니다. 이름·견종은 표시와 결과 내려받기에만 사용합니다. 견종별 예측 모델은 학습하지 않았습니다.

## 실제 머신러닝 흐름

1. CSV 형식·값·라벨·가상 자료 표시를 검증합니다.
2. 숫자는 StandardScaler, 크기·복용 여부는 OneHotEncoder로 변환합니다.
3. Random Forest가 제공된 가상 라벨 3개를 학습합니다.
4. K-Means가 동일한 입력 특징에서 생활 군집을 학습합니다.
5. Nearest Neighbors가 전처리된 사례의 검색 구조를 학습합니다.
6. 사용자의 새 설문을 세 모델에 실제로 전달해 결과 화면에 표시합니다.
7. 질환 참고정보와 진료 안내는 문헌·안전 규칙으로 별도 계산합니다.

수치가 표준화되고 범주가 원핫 인코딩된 공간의 유클리드 거리로 유사 사례를 정합니다. 거리는 확률이 아니며 건강 상태가 같다는 보증도 아닙니다. 동일 개체의 반복 기록은 검색 결과에서 중복으로 표시하지 않습니다.

`ID`, `이름`, 자유문장 `추가증상`, 정답 `가상건강상태라벨`, 정답 설명 `판단주요특징`, `데이터구분`은 분류 입력에서 제외했습니다. **정답 설명을 보고 정답을 맞히는 데이터 누수**를 방지합니다. ID는 학습·평가 분할과 사례 구분에 사용합니다.

## 학습과 평가

```powershell
.\.venv\Scripts\python.exe train.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

다른 경로에 같은 스키마의 가상 자료를 준비한 경우:

```powershell
.\.venv\Scripts\python.exe train.py --data data/dog_data.csv --output models/dog_model.joblib
```

같은 ID 또는 완전히 같은 모델 입력은 같은 그룹으로 묶습니다. 다섯 개 그룹 분할마다 전처리와 분류기를 학습 부분에서 새로 학습하고, 한 번도 그 분할의 학습에 사용하지 않은 평가 행을 예측합니다. 평가 결과를 합쳐 성능을 계산한 뒤 배포 모델은 전체 100건으로 다시 학습합니다.

| 평가 항목 | 결과 |
|---|---:|
| 5개 그룹 교차검증 정확도 | 91.0% |
| Macro F1 | 0.904 |
| 최빈 라벨만 예측한 기준선 | 38.0% |
| 각 분할의 학습·평가 그룹 중복 | 0 |

**91%는 가상 라벨을 재현한 결과입니다. 실제 질병을 맞히는 정확도나 질병 발생 확률이 아닙니다.** 상세 성능과 혼동행렬은 `models/metrics.json`, 모델 설명은 `MODEL_CARD.md`에 있습니다. 자료 수가 100건이라는 것만으로 실제 건강 판단 성능을 보장하지 않습니다.

이 버전의 학습기는 가상 자료만 받습니다. 실제 자료를 쓰려면 출처·동의·확진·시점·라벨 정의와 검증 목표를 따로 설계해야 합니다. `데이터구분`만 바꾸면 실제 발병 모델로 전환되는 구조가 아닙니다.

## 건강 참고정보와 진료 안내

`condition_guide.csv`의 12개 항목은 문헌을 바탕으로 개발자가 작성한 참고 연결입니다. `trigger`는 코드에 정의한 허용 조건 키로만 해석하고 CSV의 문자열을 코드로 실행하지 않습니다. 예를 들어 음수·배뇨 증가를 함께 응답하면 신장·내분비 관련 참고 항목을 보여 주지만 질환의 순위를 매기지 않습니다. 쿠싱증후군·췌장염·감염성 호흡기 질환·슬개골 탈구의 연결 조건과 출처를 추가했습니다.

호흡곤란, 의식 저하, 배뇨 불능, 복부팽창을 동반한 헛구역질 등 사용자가 선택한 긴급 징후는 **AI 분류에 관계없이 먼저 안내**합니다. 구토·설사 등의 지속 시간은 별도로 확인합니다. 해당 항목은 현재 학습 CSV에 없어 ML 변수에는 추가하지 않았습니다.

진료 안내는 선택한 일부 징후에 대한 문헌 기반 안내입니다. 모든 응급상황을 포괄하지 않으며, 안내가 표시되지 않더라도 안전함을 뜻하지 않습니다. 체중 평균은 가상 자료의 요약이며 적정 체중·비만 판정용이 아닙니다. 나이만으로 노령·질병을 단정하지 않습니다. 임상 현장에서의 외부 검증이나 수의사의 개별 검토는 수행하지 않았습니다.

주요 출처:

- [Merck: When to See a Veterinarian](https://www.merckvetmanual.com/multimedia/table/when-to-see-a-veterinarian)
- [AAHA: Canine Life Stage Definitions](https://www.aaha.org/resources/life-stage-canine-2019/canine-life-stage-definitions/)
- [AAHA: Nutritional Screening Evaluation](https://www.aaha.org/resources/2021-aaha-nutrition-and-weight-management-guidelines/screening-evaluation/)
- [ACVS: Gastric Dilatation-Volvulus](https://www.acvs.org/small-animal/gastric-dilatation-volvulus/)
- 기타 개별 질환 출처는 `data/condition_guide.csv`에 기록했습니다.

## 실제 질병 발생 확률을 위해 추가로 필요한 것

웹앱의 **질병 확률 데이터** 메뉴에서 현재 자료의 부족한 항목을 확인하고, 헤더만 있는 실제 발병 자료 양식을 내려받을 수 있습니다. 현재 CSV는 100행·19열이며 기존 `ID`를 개체ID로 인식합니다. 기준일·질환코드·기준일질환없음확인·추적종료일·발병여부·확진일·확인근거·자료출처가 없어 발병 결과를 점검할 수 없습니다. 상세 작성법은 [CLINICAL_DATA.md](CLINICAL_DATA.md)에 있습니다.

질환별로 임상 검증된 진단 결과와 신규 발병 여부, 관찰 시작 시점, 추적 기간을 수집해야 합니다. 이미 병이 있는지 분류하는 작업과 앞으로 일정 기간 내 발병할 확률을 예측하는 작업은 서로 다른 목표입니다. 대표성 있는 실제 사례와 발병하지 않은 사례, 누락·중도 추적 종료 처리, 개체·시간 단위 분리, 외부 검증, 확률 보정이 필요합니다. 현재 가상 라벨 비율이나 모델 투표값을 그 확률로 대신하지 않습니다.

## 저장과 보안

웹앱은 방문자 입력을 서버 메모리에서 처리하며 파일·데이터베이스에 자동으로 축적하지 않습니다. 결과는 사용자가 CSV로 내려받을 수 있습니다. 입력 자료로 공용 모델을 자동 재학습하지 않습니다. API 키나 비밀번호를 코드에 넣을 필요가 없으며 `.streamlit/secrets.toml`은 Git에서 제외합니다.

모델 파일은 저장소에 포함한 신뢰하는 로컬 파일만 읽습니다. `.joblib`은 임의의 업로드 파일에서 불러오면 안 됩니다. 모델 환경·데이터가 바뀌면 CSV에서 다시 학습하세요.

