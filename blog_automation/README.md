# ✍️ 블로그 자동화 스튜디오

키워드 하나로 **네이버 블로그 / 티스토리** 원고를 자동 생성하고 발행하는 웹앱입니다.

## 주요 기능

| 기능 | 설명 |
|---|---|
| 🎯 키워드 → 원고 자동 작성 | 키워드를 입력하면 완성된 블로그 원고를 생성 |
| 🎨 산업군 톤 자동 적용 | IT/뷰티/맛집/건강/부동산/교육/여행 등 12개 카테고리별 문체·어미·이모지 프리셋 |
| 🖼️ 이미지 자동 처리 | 커버 이미지 자동 생성(Pillow) 또는 로컬 폴더에서 키워드 매칭 검색 후 본문 삽입 |
| ✨ 서식 자동 적용 | 소제목(H3), 인용구, 줄 구분선, 메인 키워드 **형광펜**, 보조 키워드 **볼드** 자동 처리 |
| 🚀 자동 발행 | Playwright 브라우저 자동화로 네이버/티스토리 발행 (공식 API 종료로 인한 대안) |
| 📋 수동 발행 폴백 | 서식이 유지되는 HTML 클립보드 복사 / HTML 파일 저장 |

## 빠른 시작

```bash
cd blog_automation
pip install -r requirements.txt

# (선택) 자동 발행을 쓰려면
playwright install chromium

# (선택) AI 원고 생성을 쓰려면
cp .env.example .env   # ANTHROPIC_API_KEY 입력

uvicorn app.main:app --reload
# → http://127.0.0.1:8000 접속
```

`ANTHROPIC_API_KEY` 가 없어도 **템플릿 모드**로 전체 파이프라인(생성→서식→이미지→발행)이 동작합니다.

## 사용 흐름

1. **키워드 입력** — 예: `제주도 감성 카페`
2. **카테고리 선택** — 산업군에 맞는 톤(문체, 어미, 이모지, 형광펜 색)이 자동 적용됩니다.
3. **이미지 모드 선택**
   - `자동 생성`: 키워드 기반 커버 이미지를 만들어 도입부에 삽입
   - `폴더에서 찾기`: 지정 폴더에서 파일명이 키워드와 맞는 이미지를 찾아 본문에 분산 삽입
4. **원고 생성하기** — 미리보기에서 서식이 적용된 결과 확인 (제목은 직접 수정 가능)
5. **발행** — 자동 발행 버튼 또는 `HTML 복사` 후 블로그 에디터에 붙여넣기

## 자동 발행 안내 (중요)

- **티스토리 Open API 는 2024년 2월 종료**, 네이버도 글쓰기 API 를 제공하지 않아
  자동 발행은 **Playwright 브라우저 자동화**로 동작합니다.
- 두 플랫폼 모두 자동 로그인 시 캡차/2단계 인증이 뜰 수 있으므로,
  **최초 1회 수동 로그인으로 세션을 저장**해 두는 방식을 권장합니다:

```bash
python -m app.publishers.naver     # 브라우저가 뜨면 직접 로그인 → 세션 저장
python -m app.publishers.tistory   # 카카오 계정으로 로그인 → 세션 저장
```

- 에디터 UI 가 변경되면 자동 발행이 실패할 수 있습니다. 이때는 **HTML 복사** 버튼으로
  서식이 유지된 본문을 클립보드에 담아 에디터에 붙여넣으세요.
- 자동화 발행은 각 플랫폼 약관을 확인하고 본인 계정에 대해서만 사용하세요.

## 프로젝트 구조

```
blog_automation/
├── app/
│   ├── main.py                 # FastAPI 백엔드 (API + 정적 서빙)
│   ├── content/
│   │   ├── tones.py            # 산업군 12종 톤 프리셋
│   │   ├── generator.py        # Claude API / 템플릿 원고 생성기
│   │   └── formatter.py        # 블록 → HTML 서식기 (형광펜/볼드/인용구/구분선)
│   ├── images/
│   │   └── manager.py          # 폴더 이미지 검색 + Pillow 커버 생성
│   ├── publishers/
│   │   ├── base.py             # 세션 저장/복원 공통 로직
│   │   ├── naver.py            # 네이버 스마트에디터 자동화
│   │   └── tistory.py          # 티스토리 HTML 모드 자동화
│   └── static/                 # 프론트엔드 (index.html / app.js / style.css)
├── assets/images/              # "폴더에서 찾기" 기본 이미지 폴더
├── output/                     # 생성 이미지, 내보낸 HTML, 로그인 세션
├── tests/test_core.py
├── requirements.txt
└── .env.example
```

## API 요약

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/categories` | 카테고리 목록 |
| POST | `/api/generate` | 원고 생성 (keyword, category, length, image_mode…) |
| POST | `/api/render` | 수정된 블록 재렌더링 |
| POST | `/api/images/search` | 폴더에서 키워드로 이미지 검색 |
| POST | `/api/images/generate` | 커버 이미지 생성 |
| POST | `/api/export` | 발행용 HTML 파일 저장 |
| POST | `/api/publish` | 네이버/티스토리 자동 발행 |

## 테스트

```bash
cd blog_automation
python -m pytest tests/ -v
```
