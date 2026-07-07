"""imagefactory — 템플릿 기반 이미지 자동 생성 라이브러리.

앱 안에 끼워 넣는 부품(라이브러리)으로 설계되었다.
템플릿을 한 번 정의하면, 데이터(dict)만 바꿔 끼워서
환영 카드·유튜브 썸네일·인증서·SNS 카드를 수천 장씩 찍어낸다.

기본 사용법:

    from imagefactory import Template, TextLayer, render

    tpl = Template(width=1200, height=630, background="#1a1a2e", layers=[
        TextLayer(text="{name}님, 환영합니다!", x=600, y=315,
                  anchor="mm", size=64, color="white", bold=True),
    ])
    img = render(tpl, {"name": "나라"})
    img.save("welcome.png")

대량 생성:

    from imagefactory import generate_batch
    generate_batch(tpl, rows=[{"name": "나라"}, {"name": "지수"}],
                   out_dir="out", filename="welcome_{name}.png")
"""

from .template import Template, TextLayer, ImageLayer, RectLayer
from .render import render
from .batch import generate_batch
from .fonts import find_font

__version__ = "0.1.0"

__all__ = [
    "Template",
    "TextLayer",
    "ImageLayer",
    "RectLayer",
    "render",
    "generate_batch",
    "find_font",
]
