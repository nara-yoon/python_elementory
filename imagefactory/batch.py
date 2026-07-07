"""대량 생성 — 데이터 목록(또는 CSV)을 받아 이미지를 줄줄이 찍어낸다."""

import csv
import os

from .render import render


def generate_batch(template, rows, out_dir, filename="{_index}.png",
                   image_format=None, on_each=None):
    """rows의 각 항목마다 이미지를 하나씩 만들어 out_dir에 저장한다.

    rows      : dict의 리스트, 또는 CSV 파일 경로(첫 줄이 헤더)
    filename  : 파일명 패턴. 데이터 키와 {_index}(0부터)를 쓸 수 있다.
                예: "cert_{name}.png", "thumb_{_index}.jpg"
    on_each   : 콜백 (index, path, data) — 진행 로그나 업로드 훅으로 사용
    반환값     : 저장된 파일 경로 리스트
    """
    if isinstance(rows, str):
        rows = load_csv(rows)

    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for i, row in enumerate(rows):
        name = filename.format(**row, _index=i)
        path = os.path.join(out_dir, name)
        img = render(template, row)
        if image_format or path.lower().endswith((".jpg", ".jpeg")):
            img = img.convert("RGB")  # JPEG은 알파 채널을 지원하지 않는다
        img.save(path, format=image_format)
        saved.append(path)
        if on_each:
            on_each(i, path, row)
    return saved


def load_csv(path):
    """CSV 파일을 dict 리스트로 읽는다 (첫 줄 = 헤더)."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
