"""유튜브 썸네일 — 에피소드 제목만 바꿔서 시리즈 전체를 한 번에 생성.

실행: python examples/youtube_thumbnail.py
결과: examples/output/thumb_*.png (1280x720)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from imagefactory import Template, TextLayer, RectLayer, generate_batch

template = Template(
    width=1280, height=720,
    background=("#1a1a2e", "#e94560"),
    layers=[
        RectLayer(x=0, y=520, width=1280, height=200, fill="#00000090"),
        TextLayer(text="EP.{episode}", x=70, y=80, size=52,
                  color="#f9ed69", bold=True, stroke_width=3,
                  stroke_color="#1a1a2e"),
        TextLayer(text="{title}", x=70, y=250, size=88, color="white",
                  bold=True, max_width=1140, line_spacing=1.15,
                  stroke_width=4, stroke_color="#1a1a2e"),
        TextLayer(text="파이썬 기초 강의  ·  {duration}", x=70, y=590,
                  size=40, color="#f9ed69", bold=True),
    ],
)

episodes = [
    {"episode": "01", "title": "변수와 자료형, 10분 만에 끝내기", "duration": "12:30"},
    {"episode": "02", "title": "반복문이 어려운 사람은 이것부터", "duration": "15:04"},
    {"episode": "03", "title": "함수를 알면 코드가 절반으로 준다", "duration": "18:22"},
]

out = os.path.join(os.path.dirname(__file__), "output")
paths = generate_batch(template, episodes, out, filename="thumb_ep{episode}.png")
print("\n".join(paths))
