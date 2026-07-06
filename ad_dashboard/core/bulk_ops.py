"""대량 등록 / 대량 소재 변경.

CSV 한 장으로 여러 캠페인을 여러 채널에 일괄 등록하거나,
여러 캠페인의 소재를 일괄 교체한다.

CSV 형식 (샘플: config/bulk_campaigns_sample.csv, bulk_creatives_sample.csv)
  - 대량 등록: 행 1개 = 캠페인 1개. channels/keywords/genders 는 '|' 로 구분.
  - 소재 변경: 행 1개 = (채널, 캠페인 ID) 1건.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core import storage
from core.models import CampaignSpec, CreativeSpec, LaunchResult

from . import campaign_launcher
from .collector import all_connectors

# 대량 등록 CSV 필수 컬럼
CAMPAIGN_REQUIRED = ["name", "daily_budget", "start_date", "channels"]
# 소재 변경 CSV 필수 컬럼
CREATIVE_REQUIRED = ["channel", "campaign_id", "headline"]


@dataclass
class BulkRowResult:
    """CSV 행 하나의 처리 결과."""

    row: int                      # CSV 행 번호 (1부터, 헤더 제외)
    name: str                     # 캠페인 이름 또는 ID
    results: list[LaunchResult]


def _split(value: str) -> list[str]:
    return [v.strip() for v in str(value or "").split("|") if v.strip()]


def validate_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    """빠진 필수 컬럼 목록을 반환한다(없으면 빈 리스트)."""
    return [c for c in required if c not in df.columns]


def rows_to_specs(df: pd.DataFrame) -> list[CampaignSpec]:
    """대량 등록 CSV 를 CampaignSpec 목록으로 변환한다."""
    specs: list[CampaignSpec] = []
    for _, row in df.iterrows():
        get = lambda k, d="": str(row.get(k, d) or d).strip()  # noqa: E731
        specs.append(CampaignSpec(
            name=get("name"),
            daily_budget=int(float(get("daily_budget", "0") or 0)),
            start_date=get("start_date"),
            end_date=get("end_date") or None,
            channels=_split(get("channels")),
            landing_url=get("landing_url"),
            keywords=_split(get("keywords")),
            headline=get("headline"),
            description=get("description"),
            image_url=get("image_url"),
            age_min=int(float(get("age_min"))) if get("age_min") else None,
            age_max=int(float(get("age_max"))) if get("age_max") else None,
            genders=_split(get("genders")),
            locations=_split(get("locations")) or ["KR"],
        ))
    return specs


def bulk_launch(df: pd.DataFrame, demo: bool = False) -> list[BulkRowResult]:
    """CSV(DataFrame) 의 캠페인들을 순서대로 전 채널에 등록한다."""
    out: list[BulkRowResult] = []
    for i, spec in enumerate(rows_to_specs(df), start=1):
        results = campaign_launcher.launch(spec, demo=demo)
        out.append(BulkRowResult(row=i, name=spec.name, results=results))
    return out


def bulk_update_creatives(df: pd.DataFrame, demo: bool = False) -> list[BulkRowResult]:
    """CSV(DataFrame) 의 (채널, 캠페인 ID)별로 소재를 일괄 교체한다."""
    connectors = {c.channel: c for c in all_connectors()}
    conn = storage.connect()
    out: list[BulkRowResult] = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        get = lambda k, d="": str(row.get(k, d) or d).strip()  # noqa: E731
        channel, campaign_id = get("channel"), get("campaign_id")
        creative = CreativeSpec(
            headline=get("headline"), description=get("description"),
            image_url=get("image_url"), landing_url=get("landing_url"),
        )
        connector = connectors.get(channel)
        if connector is None:
            result = LaunchResult(channel=channel, ok=False,
                                  message=f"알 수 없는 채널: {channel}")
        elif demo or not connector.is_configured():
            result = LaunchResult(
                channel=channel, ok=True, campaign_id=campaign_id,
                message="(시뮬레이션) 소재 변경 — 자격증명 등록 시 실제 API로 반영됩니다")
        else:
            result = connector.update_creative(campaign_id, creative)

        storage.save_creative_update(
            conn, channel, campaign_id, creative.headline,
            "OK" if result.ok else "FAIL", result.message)
        out.append(BulkRowResult(row=i, name=campaign_id, results=[result]))
    conn.close()
    return out
