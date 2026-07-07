"""수료증 — 명단(CSV로 대체 가능)을 넣으면 수천 장도 그대로 찍힌다.

실행: python examples/certificate.py
결과: examples/output/cert_*.png (A4 가로 비율)

CSV로 쓰려면:
    generate_batch(template, "students.csv", out, filename="cert_{name}.png")
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from imagefactory import Template, TextLayer, RectLayer, generate_batch

template = Template(
    width=1400, height=990,
    background="#fdfcf7",
    layers=[
        RectLayer(x=40, y=40, width=1320, height=910, fill="#fdfcf700",
                  outline="#b8860b", outline_width=4, radius=8),
        RectLayer(x=56, y=56, width=1288, height=878, fill="#fdfcf700",
                  outline="#b8860b", outline_width=1, radius=6),
        TextLayer(text="수 료 증", x=700, y=180, anchor="mm", size=72,
                  color="#2c3e50", bold=True),
        TextLayer(text="Certificate of Completion", x=700, y=250,
                  anchor="mm", size=26, color="#b8860b"),
        TextLayer(text="{name}", x=700, y=420, anchor="mm", size=88,
                  color="#1a1a2e", bold=True),
        TextLayer(text="위 사람은 「{course}」 과정을\n성실히 이수하였기에 이 증서를 수여합니다.",
                  x=700, y=580, anchor="mm", size=34, color="#2c3e50",
                  align="center", line_spacing=1.6),
        TextLayer(text="{date}", x=700, y=760, anchor="mm", size=28,
                  color="#555555"),
        TextLayer(text="파이썬 학교장", x=700, y=830, anchor="mm", size=32,
                  color="#2c3e50", bold=True),
    ],
)

graduates = [
    {"name": "김나라", "course": "파이썬 기초", "date": "2026년 7월 7일"},
    {"name": "이지수", "course": "파이썬 기초", "date": "2026년 7월 7일"},
]

out = os.path.join(os.path.dirname(__file__), "output")
paths = generate_batch(template, graduates, out, filename="cert_{name}.png")
print("\n".join(paths))
