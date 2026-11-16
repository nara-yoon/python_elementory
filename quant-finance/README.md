# Quant Finance Projects

퀀트금융 수업 과제 노트북과 데이터입니다.

## 폴더 구성

```
quant-finance/
├── README.md
├── requirements.txt          # 노트북 실행에 필요한 패키지
├── data/
│   ├── QuantDataR.xlsx        # 월별 개별주식·재무자료 (792개 종목, 2006-08 ~ 2020-09, 93MB)
│   └── data.csv               # 월별 시장지수·무위험이자율 등
├── notebooks/
│   ├── Assignment II Multifactor Model and Factor Extraction.ipynb   # ★ 과제 II 제출본 (코드 + 결과 + 해석)
│   ├── Project I Investment Weights.ipynb
│   ├── Project II CAPM and Price of Beta.ipynb
│   ├── Project III-1 Return Prediction using Firm Characteristics.ipynb
│   ├── Project III-2 Calculation of Factors.ipynb
│   └── Time_Series_Analysis.ipynb
└── submission/
    ├── 과제II_다요인모형과요인추출.pdf    # ★ 제출용 PDF (23쪽)
    └── 과제II_다요인모형과요인추출.html   # 브라우저에서 바로 볼 수 있는 버전
```

## 과제 II: 다요인 모형과 요인추출

**결과만 볼 때**: `submission/과제II_다요인모형과요인추출.pdf` 를 열면 됩니다. 코드, 출력, 질문별 해석이 모두 들어 있습니다.

**직접 실행할 때**

```bash
pip install -r requirements.txt
cd notebooks
jupyter notebook "Assignment II Multifactor Model and Factor Extraction.ipynb"
```

- 노트북은 `../data/QuantDataR.xlsx` 를 상대경로로 읽으므로 `notebooks/` 폴더에서 열어야 합니다.
- 처음 실행할 때 엑셀(93MB) 읽기에 1~2분 걸립니다. 이후에는 임시폴더의 캐시를 씁니다. 전체 실행은 약 2~3분입니다.
- **Colab**: `QuantDataR.xlsx` 를 `MyDrive/QuantFinance/` 에 올리고, 데이터 읽기 셀의 `drive.mount('/gdrive')` 주석을 해제하면 됩니다.
- 설정값(시차 16개월, winsorize 2%, 표본기간 2009-01 ~ 2020-07, 5분위)은 두 번째 코드 셀에서 바꿀 수 있습니다.

### 분석 내용

| 절 | 내용 |
|---|---|
| 1. 기업특성 | 논문(Han, Lee and Kang, 2020)의 6개 범주에서 17개 특성 구성 (BM, EP, SP, GPA, 자산성장률, R&D/시가, 모멘텀, 규모, 변동성, 거래회전율 등) |
| 2. 수익률 설명 모형 | Fama-MacBeth 회귀 (Newey-West t). 모형 A 동시점 / B 전부 16개월 전 / C 회계 16개월 전 + 시장 1개월 전 |
| 3. 요인 계산 | 5분위 High − Low 헤지포트폴리오, 가치가중(VW)·동일가중(EW), CAPM·3요인 알파, 누적수익률 |
| 4. 결론 및 한계 | |

### 핵심 결과

- 설명력(평균 adj. R²): 동시점 **12.0%** → 16개월 전 **5.1%**. 동시점 설명력은 당월 주가와 미공시 회계정보에서 나온 것이며 예측력이 아닙니다.
- 예측력 있는 변수: **규모(−), 매출총이익/자산(+), R&D/시가(+)**. 이상치 처리 여부와 무관하게 유의합니다.
- 헤지포트폴리오: VW 기준 유의한 요인은 규모·R&D 2개뿐이고, EW 로 바꾸면 8개로 늘어납니다. 논문의 "소형주가 이상현상 결과를 좌우한다"는 주장과 같습니다.
- 누적수익률(2009-01 ~ 2020-07, 거래비용 미반영): R&D 전략 VW 334% / EW 438%.

### 알아둘 한계

- 데이터가 표본 종료 시점 상장 종목 위주라 상장폐지 종목이 빠져 있습니다(생존편의). 규모효과가 과대평가됐을 수 있습니다.
- 업종 정보가 없어 논문처럼 금융업을 제외하지 못했습니다.
- 논문의 10분위·연 1회(6월) 재구성 대신 5분위·매월 재구성을 사용했습니다.

## 다른 노트북

Project I ~ III, Time Series 노트북은 Google Colab 용으로 작성되어 `/gdrive/MyDrive/QuantFinance/` 경로의 파일을 읽습니다.
