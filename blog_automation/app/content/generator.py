# -*- coding: utf-8 -*-
"""키워드 → 블로그 원고 생성기.

1) ANTHROPIC_API_KEY 가 설정되어 있으면 Claude API 로 고품질 원고를 생성한다.
2) 키가 없거나 호출에 실패하면 카테고리 톤 프리셋 기반 템플릿 생성기로 폴백한다.

두 경로 모두 동일한 구조를 반환한다:
    {
        "title": str,
        "blocks": [ {type, text, ...}, ... ],
        "tags": [str, ...],
        "sub_keywords": [str, ...],
        "engine": "claude" | "template",
    }
"""

import json
import os
import re

from .tones import get_preset

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

LENGTH_GUIDE = {
    "short": "전체 800~1,200자, 소제목 3개",
    "medium": "전체 1,500~2,200자, 소제목 4개",
    "long": "전체 2,500~3,500자, 소제목 5개",
}


# ---------------------------------------------------------------------------
# Claude API 경로
# ---------------------------------------------------------------------------

def _build_prompt(keyword: str, preset: dict, length: str, extra_note: str) -> str:
    emoji_rule = {
        "none": "이모지를 사용하지 않는다.",
        "light": "이모지를 글 전체에서 2~4개만 절제해서 사용한다.",
        "rich": "이모지를 문단마다 자연스럽게 사용한다.",
    }[preset["emoji"]]

    return f"""당신은 한국 블로그 전문 작가입니다. 아래 조건에 맞는 블로그 원고를 작성하세요.

[주제 키워드] {keyword}
[산업군/카테고리] {preset['label']}
[문체] {preset['voice']}
[어미 스타일] {preset['ending']}
[이모지 규칙] {emoji_rule}
[분량] {LENGTH_GUIDE.get(length, LENGTH_GUIDE['medium'])}
[추가 요청] {extra_note or '없음'}

작성 규칙:
- 검색 노출(SEO)을 고려해 키워드를 제목과 본문에 자연스럽게 녹인다. 단, 키워드 남발 금지.
- 도입부는 독자의 공감을 끌어내고, 마무리는 행동 유도(댓글/공유/방문 등)로 끝낸다.
- 소제목 구성 참고: {', '.join(preset['section_hints'])}
- 중간에 분위기를 환기하는 인용구(quote)를 1~2개 넣는다.
- 섹션 사이 흐름 전환이 필요한 곳에 divider 를 넣는다.

반드시 아래 JSON 형식만 출력하세요. JSON 외 다른 텍스트를 출력하지 마세요.
{{
  "title": "클릭을 부르는 제목 (키워드 포함)",
  "blocks": [
    {{"type": "paragraph", "text": "도입부 문단"}},
    {{"type": "heading", "text": "소제목"}},
    {{"type": "paragraph", "text": "본문 문단"}},
    {{"type": "quote", "text": "인용구"}},
    {{"type": "divider"}}
  ],
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
  "sub_keywords": ["본문에서 강조할 보조 키워드 3~5개"]
}}"""


def _generate_with_claude(keyword: str, preset: dict, length: str, extra_note: str):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": _build_prompt(keyword, preset, length, extra_note),
            }],
        )
        text = "".join(part.text for part in response.content if part.type == "text")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        if not data.get("title") or not data.get("blocks"):
            return None
        data.setdefault("tags", [keyword])
        data.setdefault("sub_keywords", [])
        data["engine"] = "claude"
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 템플릿 폴백 경로 (API 키 없이 동작)
# ---------------------------------------------------------------------------

_SECTION_BODIES = [
    (
        "{keyword}에 대해 이야기할 때 가장 먼저 짚어야 할 부분이 바로 여기입니다. "
        "많은 분들이 기본기를 건너뛰고 시작하시는데, 핵심 개념을 알고 접근하면 "
        "시행착오를 크게 줄일 수 있습니다. 특히 처음이라면 이 부분을 꼼꼼히 확인해 보세요."
    ),
    (
        "실제로 경험해 보면 기대와 다른 점들이 분명 있습니다. 장점은 확실하지만, "
        "상황에 따라 아쉬운 부분도 존재하기 때문에 {keyword}를 선택하기 전에 "
        "양쪽 모두 균형 있게 살펴보는 것이 중요합니다."
    ),
    (
        "여기서부터가 진짜 실전 팁입니다. 같은 {keyword}라도 어떻게 활용하느냐에 따라 "
        "결과가 크게 달라집니다. 아래 내용은 직접 확인하고 정리한 것이니, "
        "본인 상황에 맞게 응용해 보시길 추천합니다."
    ),
    (
        "마지막으로 가장 많이 받는 질문들을 정리해 봤습니다. {keyword}를 처음 접하는 "
        "분들이 공통적으로 궁금해하는 부분이라, 미리 알아두면 훨씬 수월하게 "
        "시작하실 수 있을 겁니다."
    ),
    (
        "지금까지의 내용을 종합해 보면, 결국 중요한 것은 자신의 목적과 상황에 맞는 "
        "선택입니다. {keyword}에 정답이 하나만 있는 것은 아니니, 오늘 정리한 기준들을 "
        "참고해서 후회 없는 결정을 내리시길 바랍니다."
    ),
]

_QUOTES = [
    "좋은 선택은 충분한 정보에서 나옵니다.",
    "{keyword}, 알고 시작하면 결과가 달라집니다.",
    "망설이는 시간에 비교하고, 비교한 만큼 확신이 생깁니다.",
]

_TITLE_TEMPLATES = [
    "{keyword} 총정리, 이 글 하나면 충분합니다",
    "{keyword} 제대로 알아보기 — 핵심만 모았습니다",
    "{keyword} 시작 전 꼭 알아야 할 것들",
]

_LENGTH_SECTIONS = {"short": 3, "medium": 4, "long": 5}


def _generate_with_template(keyword: str, preset: dict, length: str, extra_note: str):
    n_sections = _LENGTH_SECTIONS.get(length, 4)
    # 키워드 해시로 제목/인용구를 골라 같은 키워드는 같은 결과가 나오게 한다
    seed = sum(ord(ch) for ch in keyword)

    title = _TITLE_TEMPLATES[seed % len(_TITLE_TEMPLATES)].format(keyword=keyword)
    hints = preset["section_hints"]

    blocks = [
        {"type": "paragraph", "text": preset["greeting"].format(keyword=keyword)},
        {"type": "quote", "text": _QUOTES[seed % len(_QUOTES)].format(keyword=keyword)},
    ]

    for i in range(n_sections):
        hint = hints[i % len(hints)]
        blocks.append({"type": "heading", "text": f"{i + 1}. {keyword} {hint}"})
        blocks.append({
            "type": "paragraph",
            "text": _SECTION_BODIES[i % len(_SECTION_BODIES)].format(keyword=keyword),
        })
        if i < n_sections - 1:
            blocks.append({"type": "divider"})

    blocks.append({"type": "paragraph", "text": preset["closing"].format(keyword=keyword)})

    tags = [keyword.replace(" ", "")]
    tags += [f"{keyword.replace(' ', '')}{suffix}" for suffix in ("추천", "후기", "정보")]
    tags.append(preset["label"].split(" / ")[0])

    return {
        "title": title,
        "blocks": blocks,
        "tags": tags[:5],
        "sub_keywords": hints[:3],
        "engine": "template",
    }


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def generate_post(keyword: str, category: str, length: str = "medium",
                  extra_note: str = "") -> dict:
    """키워드와 카테고리로 원고를 생성한다. Claude 우선, 실패 시 템플릿."""
    preset = get_preset(category)
    result = _generate_with_claude(keyword, preset, length, extra_note)
    if result is None:
        result = _generate_with_template(keyword, preset, length, extra_note)
    result["category"] = category
    result["highlight_color"] = preset["highlight"]
    return result
