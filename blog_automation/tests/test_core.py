# -*- coding: utf-8 -*-
"""핵심 파이프라인 테스트 (API 키 없이 실행 가능)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.content.formatter import blocks_to_plain_text, render_html
from app.content.generator import generate_post
from app.content.tones import get_preset, list_categories
from app.images.manager import generate_cover, search_images


def test_categories_listed():
    cats = list_categories()
    assert len(cats) >= 10
    assert all("id" in c and "label" in c for c in cats)


def test_preset_fallback():
    assert get_preset("없는카테고리")["label"] == get_preset("it_tech")["label"]


def test_template_generation_structure():
    post = generate_post("제주도 카페", "food", length="medium")
    assert post["engine"] == "template"  # API 키 없는 환경
    assert "제주도 카페" in post["title"]
    types = {b["type"] for b in post["blocks"]}
    assert {"paragraph", "heading", "quote", "divider"} <= types
    assert post["tags"]
    # medium = 소제목 4개
    assert sum(1 for b in post["blocks"] if b["type"] == "heading") == 4


def test_generation_deterministic():
    a = generate_post("노트북 추천", "it_tech")
    b = generate_post("노트북 추천", "it_tech")
    assert a["title"] == b["title"]


def test_render_html_emphasis():
    blocks = [
        {"type": "paragraph", "text": "노트북 추천을 찾는 분들께 성능 비교가 중요합니다."},
        {"type": "heading", "text": "노트북 추천 기준"},
        {"type": "quote", "text": "좋은 선택은 정보에서 나옵니다."},
        {"type": "divider"},
    ]
    html = render_html("제목", blocks, "노트북 추천", ["성능"], "#FFF3B0", ["태그1"])
    # 메인 키워드 → 형광펜
    assert 'background-color: #FFF3B0' in html
    # 보조 키워드 → 볼드
    assert "<b>성능</b>" in html
    # 소제목에는 형광펜 없이 처리됨
    assert "<h3" in html and "<blockquote" in html
    assert "#태그1" in html


def test_render_html_escapes():
    blocks = [{"type": "paragraph", "text": "<script>alert(1)</script>"}]
    html = render_html("t", blocks, "kw", [], "#FFF3B0")
    assert "<script>" not in html


def test_plain_text():
    blocks = [
        {"type": "heading", "text": "소제목"},
        {"type": "paragraph", "text": "본문"},
    ]
    text = blocks_to_plain_text("제목", blocks, ["태그"])
    assert "■ 소제목" in text and "#태그" in text


def test_image_search_and_cover():
    with tempfile.TemporaryDirectory() as tmp:
        # 매칭 파일과 비매칭 파일 생성
        for name in ("제주도_카페_1.jpg", "random.png", "not_image.txt"):
            open(os.path.join(tmp, name), "wb").close()

        results = search_images("제주도 카페", tmp)
        assert results
        assert results[0]["path"].endswith("제주도_카페_1.jpg")
        assert all(not r["path"].endswith(".txt") for r in results)

        cover = generate_cover("제주도 카페", "여행", tmp)
        assert os.path.exists(cover)
        assert cover.endswith(".png")


def test_image_search_missing_folder():
    assert search_images("키워드", "/없는/폴더") == []
