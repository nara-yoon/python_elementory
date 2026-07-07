"""가입 환영 카드 — 앱이 신규 가입자마다 자동으로 보내는 이미지.

실행: python examples/welcome_card.py  (저장소 루트에서)
결과: examples/output/welcome_*.png
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from imagefactory import Template, TextLayer, RectLayer, generate_batch

template = Template(
    width=1080, height=566,
    background=("#0f2027", "#2c5364"),
    layers=[
        RectLayer(x=60, y=60, width=960, height=446, fill="#ffffff14",
                  radius=24, outline="#ffffff40", outline_width=2),
        TextLayer(text="WELCOME ABOARD", x=540, y=150, anchor="mm",
                  size=28, color="#7fdbca", bold=True),
        TextLayer(text="{name}님, 환영합니다!", x=540, y=250, anchor="mm",
                  size=64, color="white", bold=True, shadow=True),
        TextLayer(text="{count}번째 멤버가 되어 주셨어요", x=540, y=340,
                  anchor="mm", size=30, color="#c8d6e5"),
        TextLayer(text="myapp.example.com", x=540, y=440, anchor="mm",
                  size=22, color="#7fdbca"),
    ],
)

# 실제 앱에서는 가입 이벤트마다 render() 한 번씩 부르면 된다.
new_users = [
    {"name": "나라", "count": "1,024"},
    {"name": "지수", "count": "1,025"},
    {"name": "Alex", "count": "1,026"},
]

out = os.path.join(os.path.dirname(__file__), "output")
paths = generate_batch(template, new_users, out, filename="welcome_{name}.png")
print("\n".join(paths))
