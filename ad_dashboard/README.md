# 📊 통합 광고 대시보드

네이버 검색광고 · 네이버 GFA · 카카오 검색광고 · 카카오모먼트 · 구글 애즈(검색/GDN) · 메타 광고를
**한 번에 자동 세팅**하고, 각 광고관리자 + **GA4** + **Microsoft Clarity** 성과를
**하나의 대시보드**에서 분석하는 도구입니다.

## 빠른 시작 (데모 모드 — API 키 불필요)

```bash
cd ad_dashboard
pip install -r requirements.txt

# 1) 데모 데이터 생성 (90일치 샘플)
python cli.py collect --demo

# 2) 대시보드 실행
streamlit run app.py
```

대시보드가 처음 실행될 때 DB가 비어 있으면 데모 데이터를 자동 생성하므로,
`streamlit run app.py` 만 해도 바로 화면을 볼 수 있습니다.

## 대시보드 구성

| 탭 | 내용 |
|---|---|
| **통합 개요** | 광고비·노출·클릭·CTR·전환·ROAS KPI(직전 기간 대비 증감), 채널별 일별 추이, 채널별 광고비/ROAS 비교, 노출→클릭→세션→전환 퍼널 |
| **채널·캠페인 상세** | 채널 선택 후 캠페인 단위 성과표(CTR/CPC/CPA/ROAS)와 추이 |
| **GA4 분석** | 세션·참여율·전환·매출, 소스/매체별 세션 추이와 성과표 |
| **Clarity UX** | 데드 클릭·레이지 클릭·퀵백·스크립트 오류율 추이, 스크롤 깊이 — 랜딩페이지 품질 진단 |
| **캠페인 자동 세팅** | 폼 입력 한 번으로 선택한 전 채널에 캠페인 생성 + CSV 대량 등록/대량 소재 변경 |

## 실제 API 연동

1. `.env.example` 을 `.env` 로 복사하고 사용할 플랫폼의 자격증명을 채웁니다.
2. 필요한 추가 패키지를 설치합니다 (구글 계열만 해당):
   ```bash
   pip install google-ads google-analytics-data
   ```
3. 수집 및 세팅:
   ```bash
   python cli.py collect --days 30     # 실제 성과 수집
   python cli.py launch                # config/campaign_template.yaml 로 캠페인 자동 세팅
   ```

자격증명이 채워진 채널만 실제 API를 호출하고, 나머지는 건너뛰거나(수집)
시뮬레이션(세팅)으로 처리됩니다. 채널별로 하나씩 연동을 늘려가면 됩니다.

### 플랫폼별 자격증명 발급처

| 플랫폼 | 발급 위치 | 비고 |
|---|---|---|
| 네이버 검색광고 | [광고시스템](https://manage.searchad.naver.com) → 도구 → API 사용 관리 | 액세스 라이선스 + 비밀키 + Customer ID |
| 네이버 GFA | 네이버 영업 담당자를 통한 제휴 승인 | 폐쇄형 API — 승인 문서의 URL을 `NAVER_GFA_BASE_URL` 에 설정 |
| 카카오 키워드광고/모먼트 | [Kakao Developers](https://developers.kakao.com) → 비즈니스 → 광고 API 권한 신청 | OAuth 토큰 + 광고계정 ID |
| 구글 애즈 | [Google Ads API](https://developers.google.com/google-ads/api) | 개발자 토큰(신청 필요) + OAuth 리프레시 토큰 |
| 메타 | [Meta for Developers](https://developers.facebook.com) → Marketing API | 시스템 사용자 토큰 권장 |
| GA4 | GCP 서비스 계정 키 발급 후 GA4 속성에 뷰어 권한 부여 | `google-analytics-data` 패키지 필요 |
| Clarity | Clarity 프로젝트 → 설정 → Data Export → 토큰 발급 | 최근 1~3일 데이터만 제공, 일 10회 호출 제한 → 매일 수집해 누적 |

## 대량 등록 · 대량 소재 변경 (CSV)

대시보드의 **캠페인 자동 세팅 탭** 하단에서 CSV 를 업로드하거나, CLI 로 실행합니다:

```bash
# 캠페인 대량 등록: 행 1개 = 캠페인 1개 (channels/keywords 는 | 로 구분)
python cli.py bulk-launch --file config/bulk_campaigns_sample.csv --demo

# 소재 대량 변경: 행 1개 = (채널, 캠페인 ID) 1건
python cli.py bulk-creative --file config/bulk_creatives_sample.csv --demo
```

- **대량 등록 CSV** 필수 컬럼: `name, daily_budget, start_date, channels`
  (선택: `end_date, landing_url, keywords, headline, description, image_url,
  age_min, age_max, genders, locations`)
- **소재 변경 CSV** 필수 컬럼: `channel, campaign_id, headline`
  (선택: `description, image_url, landing_url`)
- 대부분의 플랫폼은 소재 "수정" 대신 **새 소재 등록** 방식을 권장하므로,
  소재 변경은 캠페인 하위 광고그룹(광고세트)마다 새 소재를 추가합니다.
  기존 소재는 확인 후 각 광고관리자에서 중지하세요.
- 구글 GDN 반응형 디스플레이 소재는 이미지 에셋 업로드가 선행돼야 해서
  API 일괄 변경 대상에서 제외됩니다(검색 캠페인은 RSA 자동 등록 지원).
- 모든 변경 이력은 `creative_updates` 테이블에 남고 대시보드에서 확인할 수 있습니다.

## 자동화 (매일 수집)

crontab 에 등록하면 매일 아침 최신 데이터가 쌓입니다:

```cron
0 7 * * * cd /path/to/ad_dashboard && python cli.py collect --days 3
```

## 구조

```
ad_dashboard/
├── app.py                    # Streamlit 대시보드
├── cli.py                    # collect / launch CLI
├── config/
│   └── campaign_template.yaml  # 통합 캠페인 템플릿(자동 세팅 입력)
├── connectors/               # 광고 플랫폼 커넥터 (생성 + 성과 수집)
│   ├── base.py               #   공통 인터페이스
│   ├── naver_searchad.py     #   네이버 검색광고 (HMAC 서명 인증)
│   ├── naver_gfa.py          #   네이버 GFA
│   ├── kakao_keyword.py      #   카카오 키워드광고
│   ├── kakao_moment.py       #   카카오모먼트
│   ├── google_ads.py         #   구글 검색 + GDN
│   └── meta_ads.py           #   메타 Graph API
├── analytics/
│   ├── ga4.py                # GA4 Data API
│   └── clarity.py            # Clarity Data Export API
└── core/
    ├── models.py             # 통합 스키마 (DailyMetric 등)
    ├── storage.py            # SQLite 적재/조회
    ├── collector.py          # 전 채널 수집 오케스트레이터
    ├── campaign_launcher.py  # 전 채널 캠페인 자동 세팅
    └── demo_data.py          # 데모 데이터 생성기
```

## 주의사항

- 캠페인 자동 세팅 시 구글/메타는 **일시중지(PAUSED) 상태**로 생성됩니다.
  소재 검수 후 각 광고관리자에서 직접 활성화하세요 (과금 사고 방지).
- 네이버 GFA API 는 제휴 승인이 필요한 폐쇄형입니다. 승인 후 받은 문서와
  엔드포인트가 다르면 `connectors/naver_gfa.py` 상단 상수만 수정하면 됩니다.
- `.env` 와 `data/*.db` 는 git 에 커밋되지 않습니다 (.gitignore 처리).
