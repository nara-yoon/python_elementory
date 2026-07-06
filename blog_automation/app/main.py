# -*- coding: utf-8 -*-
"""블로그 자동화 웹앱 — FastAPI 백엔드.

실행:  uvicorn app.main:app --reload  (blog_automation 디렉터리에서)
"""

import os
import re
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .content.formatter import blocks_to_plain_text, render_html
from .content.generator import generate_post
from .content.tones import get_preset, list_categories
from .images.manager import generate_cover, search_images
from .publishers import naver as naver_pub
from .publishers import tistory as tistory_pub
from .publishers.base import PublishError, has_session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
GENERATED_IMG_DIR = os.path.join(OUTPUT_DIR, "images")
DEFAULT_IMAGE_FOLDER = os.environ.get(
    "BLOG_IMAGE_FOLDER", os.path.join(BASE_DIR, "assets", "images")
)

app = FastAPI(title="Blog Automation", version="1.0.0")


# ---------------------------------------------------------------------------
# 요청/응답 모델
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    category: str = "it_tech"
    length: str = "medium"                  # short | medium | long
    extra_note: str = ""                    # 추가 요청사항
    image_mode: str = "generate"            # generate | folder | none
    image_folder: str = ""                  # folder 모드에서 사용할 경로


class RenderRequest(BaseModel):
    title: str
    blocks: list
    keyword: str
    sub_keywords: list = []
    highlight_color: str = "#FFF3B0"
    tags: list = []


class ImageSearchRequest(BaseModel):
    keyword: str
    folder: str = ""


class PublishRequest(BaseModel):
    platform: str                           # naver | tistory
    title: str
    blocks: list = []
    html: str = ""
    tags: list = []
    headless: bool = True


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "claude_api": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "sessions": {"naver": has_session("naver"), "tistory": has_session("tistory")},
    }


@app.get("/api/categories")
def categories():
    return list_categories()


@app.post("/api/generate")
def generate(req: GenerateRequest):
    post = generate_post(req.keyword, req.category, req.length, req.extra_note)

    # 이미지 처리
    images = []
    if req.image_mode == "folder":
        folder = req.image_folder or DEFAULT_IMAGE_FOLDER
        found = search_images(req.keyword, folder, limit=6)
        images = [item["path"] for item in found[:3]]
    elif req.image_mode == "generate":
        preset = get_preset(req.category)
        cover = generate_cover(req.keyword, preset["label"], GENERATED_IMG_DIR)
        images = [cover]

    # 이미지를 본문에 삽입: 첫 이미지는 도입부 뒤, 나머지는 소제목 뒤에 분산
    blocks = post["blocks"]
    if images:
        insert_positions = []
        heading_indexes = [i for i, b in enumerate(blocks) if b.get("type") == "heading"]
        insert_positions.append(1)  # 도입부 문단 뒤
        # 소제목 다음다음 위치(해당 섹션 본문 뒤)에 분산 배치
        for i, hi in enumerate(heading_indexes[1::2]):
            insert_positions.append(hi + 2)
        offset = 0
        for pos, src in zip(insert_positions, images):
            block = {
                "type": "image",
                "src": f"/api/image-file?path={src}",
                "local_path": src,
                "alt": post["title"],
            }
            blocks.insert(min(pos + offset, len(blocks)), block)
            offset += 1

    html = render_html(
        post["title"], blocks, req.keyword, post.get("sub_keywords", []),
        post.get("highlight_color", "#FFF3B0"), post.get("tags", []),
    )
    plain = blocks_to_plain_text(post["title"], blocks, post.get("tags", []))

    return {**post, "blocks": blocks, "html": html, "plain_text": plain}


@app.post("/api/render")
def render(req: RenderRequest):
    """블록을 수정한 뒤 다시 HTML 로 렌더링."""
    html = render_html(req.title, req.blocks, req.keyword, req.sub_keywords,
                       req.highlight_color, req.tags)
    return {"html": html,
            "plain_text": blocks_to_plain_text(req.title, req.blocks, req.tags)}


@app.post("/api/images/search")
def images_search(req: ImageSearchRequest):
    folder = req.folder or DEFAULT_IMAGE_FOLDER
    results = search_images(req.keyword, folder)
    return {"folder": folder, "images": [
        {"path": item["path"], "score": item["score"],
         "url": f"/api/image-file?path={item['path']}"}
        for item in results
    ]}


@app.post("/api/images/generate")
def images_generate(req: ImageSearchRequest):
    path = generate_cover(req.keyword, "", GENERATED_IMG_DIR)
    return {"path": path, "url": f"/api/image-file?path={path}"}


@app.get("/api/image-file")
def image_file(path: str):
    """로컬 이미지 파일 서빙 (이미지 폴더/생성 폴더 내부만 허용)."""
    real = os.path.realpath(path)
    allowed_roots = [
        os.path.realpath(DEFAULT_IMAGE_FOLDER),
        os.path.realpath(GENERATED_IMG_DIR),
        os.path.realpath(os.environ.get("BLOG_IMAGE_FOLDER", DEFAULT_IMAGE_FOLDER)),
    ]
    if not any(real.startswith(root + os.sep) or real == root for root in allowed_roots):
        raise HTTPException(403, "허용된 이미지 폴더 밖의 파일입니다.")
    if not os.path.isfile(real):
        raise HTTPException(404, "파일을 찾을 수 없습니다.")
    return FileResponse(real)


@app.post("/api/export")
def export_html(req: RenderRequest):
    """발행용 HTML 파일로 저장 (수동 붙여넣기 폴백)."""
    html = render_html(req.title, req.blocks, req.keyword, req.sub_keywords,
                       req.highlight_color, req.tags)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe = re.sub(r"[^\w가-힣-]+", "_", req.title)[:40] or "post"
    path = os.path.join(OUTPUT_DIR, f"{safe}_{int(time.time())}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html>\n<meta charset='utf-8'>\n<title>{req.title}</title>\n{html}")
    return {"path": path}


@app.post("/api/publish")
async def publish(req: PublishRequest):
    try:
        if req.platform == "naver":
            return await naver_pub.publish(req.title, req.blocks, req.tags,
                                           headless=req.headless)
        if req.platform == "tistory":
            if not req.html:
                raise HTTPException(400, "티스토리 발행에는 html 필드가 필요합니다.")
            return await tistory_pub.publish(req.title, req.html, req.tags,
                                             headless=req.headless)
        raise HTTPException(400, f"지원하지 않는 플랫폼: {req.platform}")
    except PublishError as exc:
        raise HTTPException(422, str(exc))


# 정적 프론트엔드 (마지막에 마운트해야 /api 라우트를 가리지 않음)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"),
                           html=True), name="static")
