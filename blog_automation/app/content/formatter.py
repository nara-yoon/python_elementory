# -*- coding: utf-8 -*-
"""원고 블록 → 블로그용 HTML 서식기.

블록 구조 (dict):
    {"type": "heading",   "text": "..."}          # 소제목
    {"type": "paragraph", "text": "..."}          # 본문 문단
    {"type": "quote",     "text": "..."}          # 인용구
    {"type": "divider"}                            # 줄 구분선
    {"type": "image",     "src": "...", "alt": ""} # 이미지

자동 강조 규칙:
    - 메인 키워드          → 형광펜(배경색) + 볼드
    - 보조 키워드          → 볼드
    - 소제목/인용구 내부는 형광펜 대신 볼드만 적용
"""

import html
import re


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _emphasize(text: str, main_keyword: str, sub_keywords: list, highlight_color: str,
               allow_highlight: bool = True) -> str:
    """이스케이프된 텍스트에 볼드/형광펜 마크업을 입힌다."""
    escaped = _escape(text)

    def highlight_repl(match):
        word = match.group(0)
        if allow_highlight:
            return (
                f'<b><span style="background-color: {highlight_color};">{word}</span></b>'
            )
        return f"<b>{word}</b>"

    # 메인 키워드: 문단당 최대 2회만 강조해 과한 형광펜을 방지
    if main_keyword:
        pattern = re.compile(re.escape(_escape(main_keyword)), re.IGNORECASE)
        escaped = pattern.sub(highlight_repl, escaped, count=2)

    # 보조 키워드: 각 1회 볼드
    for keyword in sub_keywords or []:
        keyword = keyword.strip()
        if not keyword or keyword == main_keyword:
            continue
        pattern = re.compile(re.escape(_escape(keyword)), re.IGNORECASE)
        # 이미 태그 안에 들어간 단어를 다시 감싸지 않도록 태그 밖 텍스트만 대상
        parts = re.split(r"(<[^>]+>)", escaped)
        replaced = False
        for i, part in enumerate(parts):
            if part.startswith("<") or replaced:
                continue
            new_part, n = pattern.subn(lambda m: f"<b>{m.group(0)}</b>", part, count=1)
            if n:
                parts[i] = new_part
                replaced = True
        escaped = "".join(parts)

    return escaped


def render_block(block: dict, main_keyword: str, sub_keywords: list, highlight_color: str) -> str:
    btype = block.get("type", "paragraph")

    if btype == "heading":
        text = _emphasize(block.get("text", ""), main_keyword, sub_keywords,
                          highlight_color, allow_highlight=False)
        return (
            '<h3 style="font-size: 1.35em; font-weight: 700; margin: 2em 0 0.8em; '
            'padding-left: 12px; border-left: 4px solid #333;">'
            f"{text}</h3>"
        )

    if btype == "paragraph":
        text = _emphasize(block.get("text", ""), main_keyword, sub_keywords, highlight_color)
        return f'<p style="line-height: 1.9; margin: 0 0 1.2em;">{text}</p>'

    if btype == "quote":
        text = _emphasize(block.get("text", ""), main_keyword, sub_keywords,
                          highlight_color, allow_highlight=False)
        return (
            '<blockquote style="margin: 1.8em 0; padding: 1em 1.4em; '
            'border-left: 4px solid #bbb; background: #f7f7f7; '
            'font-style: italic; color: #444;">'
            f"{text}</blockquote>"
        )

    if btype == "divider":
        return (
            '<div style="text-align: center; margin: 2.2em 0; color: #bbb; '
            'letter-spacing: 0.6em;">◦ ◦ ◦</div>'
        )

    if btype == "image":
        src = html.escape(block.get("src", ""), quote=True)
        alt = html.escape(block.get("alt", ""), quote=True)
        caption = ""
        if block.get("caption"):
            caption = (
                '<figcaption style="text-align: center; color: #999; '
                f'font-size: 0.85em; margin-top: 0.5em;">{_escape(block["caption"])}</figcaption>'
            )
        return (
            '<figure style="margin: 1.8em 0; text-align: center;">'
            f'<img src="{src}" alt="{alt}" style="max-width: 100%; border-radius: 8px;" />'
            f"{caption}</figure>"
        )

    return ""


def render_html(title: str, blocks: list, main_keyword: str, sub_keywords: list,
                highlight_color: str = "#FFF3B0", tags: list = None) -> str:
    """전체 원고를 발행용 HTML로 렌더링한다."""
    body = "\n".join(
        render_block(block, main_keyword, sub_keywords, highlight_color)
        for block in blocks
    )
    tag_html = ""
    if tags:
        tag_line = " ".join(f"#{_escape(tag)}" for tag in tags)
        tag_html = (
            '\n<p style="margin-top: 2.5em; color: #7a8ba8; font-size: 0.9em;">'
            f"{tag_line}</p>"
        )
    return (
        '<div class="blog-post" style="font-size: 16px; color: #222; word-break: keep-all;">\n'
        f"{body}{tag_html}\n</div>"
    )


def blocks_to_plain_text(title: str, blocks: list, tags: list = None) -> str:
    """편집기 직접 붙여넣기용 플레인 텍스트 버전."""
    lines = [title, ""]
    for block in blocks:
        btype = block.get("type")
        if btype == "heading":
            lines += ["", f"■ {block.get('text', '')}", ""]
        elif btype == "paragraph":
            lines += [block.get("text", ""), ""]
        elif btype == "quote":
            lines += [f"❝ {block.get('text', '')} ❞", ""]
        elif btype == "divider":
            lines += ["- - - - - - - - - -", ""]
        elif btype == "image":
            lines += [f"[이미지: {block.get('alt') or block.get('src', '')}]", ""]
    if tags:
        lines.append(" ".join(f"#{tag}" for tag in tags))
    return "\n".join(lines)
