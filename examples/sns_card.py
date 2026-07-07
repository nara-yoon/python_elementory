"""SNS 공유 카드(OG 이미지) — 블로그 글마다 자동 생성되는 1200x630 카드.

실행: python examples/sns_card.py
결과: examples/output/og_*.png

JSON 템플릿 로드 예시도 겸한다 — 템플릿을 DB나 설정 파일에
넣어 두고 코드 수정 없이 디자인을 바꿀 수 있다.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from imagefactory import Template, generate_batch

TEMPLATE_JSON = """
{
  "width": 1200, "height": 630,
  "background": ["#232526", "#414345"],
  "layers": [
    {"kind": "rect", "x": 0, "y": 0, "width": 16, "height": 630,
     "fill": "#e94560"},
    {"kind": "text", "text": "{category}", "x": 80, "y": 90,
     "size": 28, "color": "#e94560", "bold": true},
    {"kind": "text", "text": "{title}", "x": 80, "y": 170, "size": 64,
     "color": "white", "bold": true, "max_width": 1040,
     "line_spacing": 1.25},
    {"kind": "text", "text": "{author}  ·  {date}", "x": 80, "y": 520,
     "size": 28, "color": "#c8d6e5"}
  ]
}
"""

template = Template.from_json(TEMPLATE_JSON)

posts = [
    {"category": "TUTORIAL", "title": "Pillow로 이미지 1만 장을 3분 만에 만드는 법",
     "author": "nara", "date": "2026-07-07"},
    {"category": "DEV LOG", "title": "이미지 생성 API를 부품처럼 설계하기",
     "author": "nara", "date": "2026-07-07"},
]

out = os.path.join(os.path.dirname(__file__), "output")
paths = generate_batch(template, posts, out, filename="og_{_index}.png")
print("\n".join(paths))
