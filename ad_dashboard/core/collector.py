"""성과 데이터 수집기.

설정된 커넥터에서 성과를 가져와 통합 스키마로 SQLite에 적재한다.
자격증명이 하나도 없으면(또는 --demo) 데모 데이터를 생성해 채운다.
"""
from __future__ import annotations

from datetime import date, timedelta

from analytics.clarity import ClarityConnector
from analytics.ga4 import Ga4Connector
from connectors.base import AdPlatformConnector
from connectors.google_ads import GoogleAdsConnector
from connectors.kakao_keyword import KakaoKeywordConnector
from connectors.kakao_moment import KakaoMomentConnector
from connectors.meta_ads import MetaAdsConnector
from connectors.naver_gfa import NaverGfaConnector
from connectors.naver_searchad import NaverSearchAdConnector

from . import demo_data, storage


def all_connectors() -> list[AdPlatformConnector]:
    return [
        NaverSearchAdConnector(),
        NaverGfaConnector(),
        KakaoKeywordConnector(),
        KakaoMomentConnector(),
        GoogleAdsConnector("SEARCH"),
        GoogleAdsConnector("DISPLAY"),
        MetaAdsConnector(),
    ]


def collect(days: int = 30, demo: bool = False, end: date | None = None) -> dict[str, int]:
    """최근 days 일치 데이터를 수집해 DB에 적재하고 채널별 건수를 반환한다."""
    end = end or (date.today() - timedelta(days=1))
    start = end - timedelta(days=days - 1)
    conn = storage.connect()
    counts: dict[str, int] = {}

    connectors = all_connectors()
    any_configured = any(c.is_configured() for c in connectors)

    if demo or not any_configured:
        # 데모 모드: 90일치 일괄 생성
        metrics = demo_data.generate_metrics(end, days=max(days, 90))
        counts["demo_metrics"] = storage.upsert_metrics(conn, metrics)
        counts["demo_ga4"] = storage.upsert_ga4(conn, demo_data.generate_ga4(metrics))
        counts["demo_clarity"] = storage.upsert_clarity(
            conn, demo_data.generate_clarity(metrics))
        conn.close()
        return counts

    for connector in connectors:
        if not connector.is_configured():
            counts[connector.channel] = -1  # 미설정 표시
            continue
        rows = connector.fetch_daily_metrics(start, end)
        counts[connector.channel] = storage.upsert_metrics(conn, rows)

    ga4 = Ga4Connector()
    if ga4.is_configured():
        counts["ga4"] = storage.upsert_ga4(conn, ga4.fetch_daily(start, end))

    clarity = ClarityConnector()
    if clarity.is_configured():
        counts["clarity"] = storage.upsert_clarity(conn, clarity.fetch_daily(3))

    conn.close()
    return counts
