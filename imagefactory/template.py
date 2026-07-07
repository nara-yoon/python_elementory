"""템플릿과 레이어 정의.

Template = 캔버스(크기 + 배경) + 레이어 목록.
레이어의 문자열 속성에는 "{name}"처럼 자리표시자를 넣을 수 있고,
render() 호출 때 데이터로 치환된다.

JSON으로도 정의할 수 있어서, 템플릿을 코드 밖(DB·설정 파일)에
보관했다가 불러 쓸 수 있다. Template.from_dict / from_json 참고.
"""

import json
from dataclasses import dataclass, field


@dataclass
class TextLayer:
    """텍스트 레이어.

    x, y와 anchor로 위치를 잡는다. anchor는 Pillow 규칙을 따른다
    (두 글자: 가로 l/m/r + 세로 a/m/d — 예: "mm"은 정중앙 기준).
    max_width를 주면 그 폭에 맞춰 자동 줄바꿈한다.
    """

    text: str
    x: int
    y: int
    size: int = 32
    color: str = "black"
    font: str = None          # 폰트 파일 경로 또는 파일명 키워드. 없으면 자동 선택
    bold: bool = False
    anchor: str = "la"        # 기본: 왼쪽 위 기준
    max_width: int = None     # 지정하면 단어 단위 자동 줄바꿈
    align: str = "left"       # 여러 줄일 때 정렬: left/center/right
    line_spacing: float = 1.2
    stroke_width: int = 0
    stroke_color: str = "black"
    shadow: bool = False
    shadow_color: str = "#00000080"
    shadow_offset: int = 3

    kind = "text"


@dataclass
class ImageLayer:
    """이미지 레이어 (로고, 아바타, 배경 사진 등).

    source는 파일 경로이며 자리표시자를 쓸 수 있다 (예: "{avatar_path}").
    circle=True면 원형으로 잘라낸다(프로필 사진용).
    """

    source: str
    x: int
    y: int
    width: int = None
    height: int = None
    anchor: str = "la"        # "la"(왼쪽 위) 또는 "mm"(중앙)
    circle: bool = False
    radius: int = 0           # 둥근 모서리 반지름

    kind = "image"


@dataclass
class RectLayer:
    """사각형 레이어 (배경 박스, 배지, 구분선 등)."""

    x: int
    y: int
    width: int
    height: int
    fill: str = "white"
    radius: int = 0
    outline: str = None
    outline_width: int = 1

    kind = "rect"


_LAYER_TYPES = {"text": TextLayer, "image": ImageLayer, "rect": RectLayer}


@dataclass
class Template:
    """이미지 한 종류의 설계도.

    background는 세 가지를 받는다:
      - 단색:      "#1a1a2e" 또는 "white"
      - 그라데이션: ("#0f2027", "#2c5364")  — 위에서 아래로
      - 이미지:    "path/to/bg.png" (파일 경로, 자리표시자 가능)
    """

    width: int
    height: int
    background: object = "white"
    layers: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, spec):
        layers = []
        for item in spec.get("layers", []):
            item = dict(item)
            kind = item.pop("kind")
            layers.append(_LAYER_TYPES[kind](**item))
        background = spec.get("background", "white")
        if isinstance(background, list):
            background = tuple(background)
        return cls(width=spec["width"], height=spec["height"],
                   background=background, layers=layers)

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))
