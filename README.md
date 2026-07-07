# imagefactory

이미지를 자동으로 찍어내는 파이썬 라이브러리.

유튜브 썸네일, SNS 카드, 수료증, 환영 이미지 — 사람이 한 장씩 그리지 않고
**템플릿 하나 + 데이터**로 수천 장을 코드로 만들어낸다.

눈에 띄는 앱이 아니라, 다른 앱 속에서 조용히 돌아가는 **부품**이다.
예를 들어 앱이 신규 가입자마다 환영 이미지를 자동으로 만들어 보내고 싶을 때,
가입 이벤트 핸들러에서 `render()` 한 번 부르면 끝난다.

## 설치

```bash
pip install pillow
```

이 저장소를 클론한 뒤 `imagefactory/` 폴더를 프로젝트에 넣거나
저장소 루트에서 임포트하면 된다. 의존성은 Pillow 하나뿐이다.

## 3줄 사용법

```python
from imagefactory import Template, TextLayer, render

tpl = Template(width=1200, height=630, background="#1a1a2e", layers=[
    TextLayer(text="{name}님, 환영합니다!", x=600, y=315,
              anchor="mm", size=64, color="white", bold=True),
])
render(tpl, {"name": "나라"}).save("welcome.png")
```

## 대량 생성 (수천 장)

```python
from imagefactory import generate_batch

users = [{"name": "나라"}, {"name": "지수"}, ...]          # dict 리스트
generate_batch(tpl, users, out_dir="out", filename="welcome_{name}.png")

# CSV(첫 줄이 헤더)를 그대로 넣어도 된다
generate_batch(tpl, "students.csv", out_dir="out", filename="cert_{name}.png")
```

## 템플릿 구성 요소

| 요소 | 설명 |
|---|---|
| `Template` | 캔버스 크기 + 배경 + 레이어 목록 |
| `TextLayer` | 텍스트. 자동 줄바꿈(`max_width`), 굵기, 외곽선, 그림자, 정렬 |
| `ImageLayer` | 로고·아바타·사진. 원형 자르기(`circle`), 둥근 모서리(`radius`) |
| `RectLayer` | 배경 박스·배지·구분선. 반투명 색, 둥근 모서리, 테두리 |

배경(`background`)은 세 가지를 받는다:

- 단색: `"#1a1a2e"`
- 그라데이션(위→아래): `("#0f2027", "#2c5364")`
- 배경 이미지: `"bg.png"`

모든 문자열 속성에 `"{key}"` 자리표시자를 쓸 수 있고 `render(tpl, data)`의
data로 치환된다. 폰트는 텍스트에 한글이 있으면 한글 폰트(나눔·Noto CJK)를
자동으로 고르며, `font=` 로 직접 지정할 수도 있다.

## 템플릿을 코드 밖에 두기

템플릿은 JSON으로도 정의된다. DB나 설정 파일에 넣어 두면
앱 코드를 고치지 않고 디자인을 바꿀 수 있다.

```python
tpl = Template.from_json(open("og_card.json").read())
```

## 예제

`examples/`에 실제로 돌아가는 예제 4종이 있다. 저장소 루트에서 실행하면
`examples/output/`에 PNG가 생성된다.

| 예제 | 내용 |
|---|---|
| `examples/welcome_card.py` | 가입 환영 카드 (그라데이션 + 그림자 텍스트) |
| `examples/youtube_thumbnail.py` | 유튜브 썸네일 1280x720 (외곽선 텍스트, 자동 줄바꿈) |
| `examples/certificate.py` | 수료증 (이중 테두리, 여러 줄 본문) |
| `examples/sns_card.py` | SNS 공유(OG) 카드 — JSON 템플릿 로드 예시 |

```bash
python examples/welcome_card.py
```

## 테스트

```bash
python -m pytest tests/
```
