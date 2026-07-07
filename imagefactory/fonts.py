"""폰트 탐색 유틸리티.

시스템에 설치된 폰트 중에서 쓸 만한 것을 자동으로 찾는다.
한글이 포함된 텍스트면 한글 지원 폰트(나눔·Noto CJK)를 우선한다.
"""

import glob
import os
from functools import lru_cache

from PIL import ImageFont

# 우선순위 순서. (regular 후보들, bold 후보들)
_KOREAN_FONTS = {
    "regular": [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ],
    "bold": [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ],
}

_LATIN_FONTS = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
}

_SEARCH_DIRS = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/.local/share/fonts"),
]


def _has_korean(text):
    return any("가" <= ch <= "힣" or "ㄱ" <= ch <= "ㆎ" for ch in text)


def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


@lru_cache(maxsize=None)
def _scan_by_keyword(keyword):
    """폰트 디렉터리에서 파일명에 keyword가 들어간 폰트를 찾는다."""
    for base in _SEARCH_DIRS:
        for ext in ("ttf", "otf", "ttc"):
            hits = glob.glob(os.path.join(base, "**", f"*{keyword}*.{ext}"), recursive=True)
            if hits:
                return sorted(hits)[0]
    return None


def find_font(text="", bold=False, preferred=None):
    """텍스트에 맞는 폰트 파일 경로를 돌려준다.

    preferred가 주어지면 그대로 쓰고(경로 또는 파일명 키워드),
    아니면 텍스트에 한글이 있는지 보고 알맞은 시스템 폰트를 고른다.
    """
    if preferred:
        if os.path.exists(preferred):
            return preferred
        hit = _scan_by_keyword(preferred)
        if hit:
            return hit
        raise FileNotFoundError(f"폰트를 찾을 수 없습니다: {preferred}")

    weight = "bold" if bold else "regular"
    table = _KOREAN_FONTS if _has_korean(text) else _LATIN_FONTS
    path = _first_existing(table[weight]) or _first_existing(_LATIN_FONTS[weight])
    if path is None:
        raise FileNotFoundError(
            "사용할 수 있는 시스템 폰트가 없습니다. "
            "TextLayer(font=...)로 폰트 파일 경로를 직접 지정하세요."
        )
    return path


@lru_cache(maxsize=128)
def load_font(path, size):
    """같은 폰트를 반복해서 열지 않도록 캐시해서 로드한다."""
    return ImageFont.truetype(path, size)
