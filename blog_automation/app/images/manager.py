# -*- coding: utf-8 -*-
"""이미지 검색 및 생성 관리자.

- search_images(keyword, folder): 로컬 폴더에서 키워드와 이름이 맞는 이미지를 찾는다.
- generate_cover(keyword, ...):   Pillow 로 키워드 커버 이미지를 생성한다 (외부 API 불필요).
"""

import hashlib
import os
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# 흔히 설치되어 있는 한글 지원 폰트 후보
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]

_PALETTES = [
    ((46, 58, 89), (95, 133, 219)),    # 딥블루
    ((64, 42, 84), (186, 104, 200)),   # 퍼플
    ((27, 77, 62), (99, 190, 123)),    # 그린
    ((120, 53, 43), (235, 148, 90)),   # 테라코타
    ((38, 50, 56), (96, 125, 139)),    # 슬레이트
    ((105, 52, 89), (232, 106, 146)),  # 핑크
]


def _tokenize(text: str) -> set:
    return {token for token in re.split(r"[\s_\-.,]+", text.lower()) if token}


def search_images(keyword: str, folder: str, limit: int = 12) -> list:
    """폴더(하위 포함)에서 파일명이 키워드와 겹치는 이미지를 점수순으로 반환."""
    if not folder or not os.path.isdir(folder):
        return []

    keyword_tokens = _tokenize(keyword)
    scored = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            stem, ext = os.path.splitext(name)
            if ext.lower() not in IMAGE_EXTS:
                continue
            path = os.path.join(root, name)
            name_tokens = _tokenize(stem)
            overlap = len(keyword_tokens & name_tokens)
            # 부분 문자열 매칭도 가점 (한글 파일명은 토큰이 안 쪼개지는 경우가 많음)
            partial = sum(
                1 for kw in keyword_tokens
                if any(kw in token or token in kw for token in name_tokens)
            )
            score = overlap * 2 + partial
            scored.append((score, path))

    scored.sort(key=lambda item: (-item[0], item[1]))
    matched = [{"path": path, "score": score} for score, path in scored if score > 0]
    if matched:
        return matched[:limit]
    # 매칭이 없으면 폴더의 이미지 자체를 후보로 제공
    return [{"path": path, "score": 0} for _score, path in scored[:limit]]


def _find_korean_font() -> str:
    """한글 렌더링이 가능한 폰트 파일 경로를 찾는다."""
    env_font = os.environ.get("BLOG_COVER_FONT")
    if env_font and os.path.exists(env_font):
        return env_font
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    # Linux: fontconfig 에 한글 지원 폰트를 질의
    try:
        out = subprocess.run(
            ["fc-list", ":lang=ko", "file"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        for line in out.splitlines():
            path = line.split(":")[0].strip()
            if path and os.path.exists(path):
                return path
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _pick_font(size: int):
    path = _find_korean_font()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def generate_cover(keyword: str, subtitle: str, out_dir: str,
                   width: int = 1200, height: int = 630) -> str:
    """키워드 기반 그라데이션 커버 이미지를 생성하고 파일 경로를 반환."""
    os.makedirs(out_dir, exist_ok=True)
    digest = hashlib.md5(f"{keyword}|{subtitle}".encode("utf-8")).hexdigest()[:10]
    out_path = os.path.join(out_dir, f"cover_{digest}.png")
    if os.path.exists(out_path):
        return out_path

    top, bottom = _PALETTES[sum(keyword.encode("utf-8")) % len(_PALETTES)]
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    # 세로 그라데이션
    for y in range(height):
        ratio = y / height
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)

    # 반투명 장식 원
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.ellipse([width - 380, -180, width + 120, 320], fill=(255, 255, 255, 26))
    odraw.ellipse([-160, height - 300, 260, height + 140], fill=(255, 255, 255, 20))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)

    # 타이틀 (길면 줄바꿈)
    title_font = _pick_font(72)
    small_font = _pick_font(30)
    max_chars = 14
    lines = [keyword[i:i + max_chars] for i in range(0, len(keyword), max_chars)][:3]

    line_height = 92
    total_height = len(lines) * line_height + 60
    y = (height - total_height) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x + 2, y + 2), line, font=title_font, fill=(0, 0, 0, 90))
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255))
        y += line_height

    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=small_font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y + 24), subtitle, font=small_font, fill=(255, 255, 255, 220))

    image.save(out_path, "PNG")
    return out_path
