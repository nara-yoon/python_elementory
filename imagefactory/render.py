"""템플릿 + 데이터 → PIL 이미지 렌더링."""

import os

from PIL import Image, ImageColor, ImageDraw

from .fonts import find_font, load_font
from .template import Template


def render(template: Template, data: dict = None) -> Image.Image:
    """템플릿에 데이터를 채워 이미지를 만든다.

    레이어의 문자열 속성 안 "{key}" 자리표시자가 data 값으로 치환된다.
    돌려주는 값은 PIL Image이므로 save()·바이트 변환·업로드 등
    호출한 쪽에서 원하는 대로 처리하면 된다.
    """
    data = data or {}
    canvas = _make_background(template, data)
    draw = ImageDraw.Draw(canvas)

    for layer in template.layers:
        if layer.kind == "text":
            _draw_text(canvas, draw, layer, data)
        elif layer.kind == "image":
            _paste_image(canvas, layer, data)
        elif layer.kind == "rect":
            _draw_rect(canvas, layer)
        else:
            raise ValueError(f"알 수 없는 레이어 종류: {layer.kind!r}")

    return canvas


def _fill(value, data):
    """문자열이면 자리표시자를 채워서 돌려준다."""
    if isinstance(value, str):
        return value.format(**data)
    return value


def _make_background(template, data):
    size = (template.width, template.height)
    bg = template.background

    if isinstance(bg, tuple) and len(bg) == 2:          # 세로 그라데이션
        return _gradient(size, bg[0], bg[1])

    if isinstance(bg, str) and os.path.splitext(bg)[1].lower() in (
            ".png", ".jpg", ".jpeg", ".webp", ".bmp"):  # 배경 이미지
        img = Image.open(_fill(bg, data)).convert("RGBA")
        return _cover_resize(img, size)

    return Image.new("RGBA", size, ImageColor.getrgb(bg) + (255,))  # 단색


def _gradient(size, top, bottom):
    top = ImageColor.getrgb(top)
    bottom = ImageColor.getrgb(bottom)
    width, height = size
    img = Image.new("RGBA", size)
    for y in range(height):
        t = y / max(height - 1, 1)
        row = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        img.paste(row + (255,), (0, y, width, y + 1))
    return img


def _cover_resize(img, size):
    """비율을 유지하며 캔버스를 꽉 채우도록 자르고 리사이즈한다."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)))
    left = (resized.width - tw) // 2
    top = (resized.height - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _draw_text(canvas, draw, layer, data):
    text = _fill(layer.text, data)
    font_path = find_font(text=text, bold=layer.bold, preferred=layer.font)
    font = load_font(font_path, layer.size)

    if layer.max_width:
        text = _wrap(draw, text, font, layer.max_width)

    kwargs = dict(
        font=font,
        fill=layer.color,
        anchor=layer.anchor if "\n" not in text else None,
        align=layer.align,
        spacing=round(layer.size * (layer.line_spacing - 1)),
        stroke_width=layer.stroke_width,
        stroke_fill=layer.stroke_color,
    )
    # 여러 줄 텍스트는 Pillow가 세로 anchor 'm'/'d'를 지원하지 않아
    # multiline용 anchor로 바꿔준다 (가로 기준만 유지).
    if "\n" in text and layer.anchor:
        kwargs["anchor"] = layer.anchor[0] + "a"

    if layer.shadow:
        shadow_pos = (layer.x + layer.shadow_offset, layer.y + layer.shadow_offset)
        shadow_kwargs = dict(kwargs, fill=layer.shadow_color,
                             stroke_width=0, stroke_fill=None)
        draw.text(shadow_pos, text, **shadow_kwargs)

    draw.text((layer.x, layer.y), text, **kwargs)


def _wrap(draw, text, font, max_width):
    """max_width(px)를 넘지 않게 단어 단위로 줄바꿈한다."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and draw.textlength(candidate, font=font) > max_width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return "\n".join(lines)


def _paste_image(canvas, layer, data):
    img = Image.open(_fill(layer.source, data)).convert("RGBA")

    if layer.width and layer.height:
        img = _cover_resize(img, (layer.width, layer.height))
    elif layer.width:
        ratio = layer.width / img.width
        img = img.resize((layer.width, round(img.height * ratio)))
    elif layer.height:
        ratio = layer.height / img.height
        img = img.resize((round(img.width * ratio), layer.height))

    if layer.circle:
        img = _mask_circle(img)
    elif layer.radius:
        img = _mask_rounded(img, layer.radius)

    x, y = layer.x, layer.y
    if layer.anchor == "mm":
        x -= img.width // 2
        y -= img.height // 2

    canvas.alpha_composite(img, (x, y))


def _mask_circle(img):
    # 안티앨리어싱을 위해 4배 크기 마스크를 만들어 줄여 쓴다.
    big = (img.width * 4, img.height * 4)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big, fill=255)
    mask = mask.resize(img.size)
    img.putalpha(mask)
    return img


def _mask_rounded(img, radius):
    big = (img.width * 4, img.height * 4)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0) + big, radius=radius * 4, fill=255)
    mask = mask.resize(img.size)
    img.putalpha(mask)
    return img


def _draw_rect(canvas, layer):
    # 반투명 색을 지원하기 위해 별도 레이어에 그려 합성한다.
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    box = (layer.x, layer.y, layer.x + layer.width, layer.y + layer.height)
    outline_kwargs = {}
    if layer.outline:
        outline_kwargs = dict(outline=layer.outline, width=layer.outline_width)
    if layer.radius:
        draw.rounded_rectangle(box, radius=layer.radius, fill=layer.fill, **outline_kwargs)
    else:
        draw.rectangle(box, fill=layer.fill, **outline_kwargs)
    canvas.alpha_composite(overlay)
