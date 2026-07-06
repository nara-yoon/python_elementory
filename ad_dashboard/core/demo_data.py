"""데모 데이터 생성기.

API 자격증명 없이도 대시보드를 바로 체험할 수 있도록,
채널별 특성(검색 vs 디스플레이의 CTR/CPC 차이 등)을 반영한
그럴듯한 90일치 샘플 데이터를 시드 고정 난수로 만든다.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from .models import ClarityDaily, DailyMetric, Ga4Daily, Channel

# 채널별 (일평균 노출, CTR%, CPC원, 전환율%, 평균 객단가)
_PROFILES: dict[str, tuple[int, float, int, float, int]] = {
    Channel.NAVER_SEARCH: (18_000, 1.9, 780, 3.2, 52_000),
    Channel.NAVER_GFA: (220_000, 0.42, 240, 0.9, 46_000),
    Channel.KAKAO_SEARCH: (9_500, 1.6, 690, 2.7, 49_000),
    Channel.KAKAO_MOMENT: (160_000, 0.38, 210, 0.8, 44_000),
    Channel.GOOGLE_SEARCH: (14_000, 2.3, 850, 3.6, 55_000),
    Channel.GOOGLE_GDN: (260_000, 0.35, 180, 0.7, 43_000),
    Channel.META: (190_000, 0.55, 260, 1.1, 47_000),
}

# 채널 -> GA4 소스/매체 매핑 (데모용)
_SOURCE_MEDIUM: dict[str, str] = {
    Channel.NAVER_SEARCH: "naver / cpc",
    Channel.NAVER_GFA: "naver_gfa / display",
    Channel.KAKAO_SEARCH: "kakao / cpc",
    Channel.KAKAO_MOMENT: "kakao_moment / display",
    Channel.GOOGLE_SEARCH: "google / cpc",
    Channel.GOOGLE_GDN: "google / display",
    Channel.META: "facebook / paid_social",
}

_CAMPAIGNS = ["브랜드", "신제품 런칭", "리타겟팅"]


def _season(day: date) -> float:
    """요일/추세 가중치: 주말은 낮고, 최근으로 올수록 완만히 성장."""
    weekday_factor = 0.72 if day.weekday() >= 5 else 1.0
    wave = 1 + 0.15 * math.sin(day.toordinal() / 9)
    return weekday_factor * wave


def generate_metrics(end: date, days: int = 90) -> list[DailyMetric]:
    rng = random.Random(42)
    out: list[DailyMetric] = []
    start = end - timedelta(days=days - 1)
    for ch, (imp_base, ctr, cpc, cvr, aov) in _PROFILES.items():
        for i, camp in enumerate(_CAMPAIGNS):
            camp_weight = (0.45, 0.35, 0.20)[i]
            day = start
            growth = 1.0
            while day <= end:
                growth = 1 + (day - start).days / days * 0.25
                noise = rng.uniform(0.8, 1.2)
                impressions = int(imp_base * camp_weight * _season(day) * growth * noise)
                clicks = int(impressions * ctr / 100 * rng.uniform(0.85, 1.15))
                cost = clicks * cpc * rng.uniform(0.9, 1.1)
                conversions = clicks * cvr / 100 * rng.uniform(0.7, 1.3)
                revenue = conversions * aov * rng.uniform(0.85, 1.15)
                out.append(DailyMetric(
                    date=day, channel=ch.value,
                    campaign_id=f"demo_{ch.value}_{i+1}",
                    campaign_name=f"[데모] {camp}",
                    impressions=impressions, clicks=clicks,
                    cost=round(cost), conversions=round(conversions, 1),
                    revenue=round(revenue),
                ))
                day += timedelta(days=1)
    return out


def generate_ga4(metrics: list[DailyMetric]) -> list[Ga4Daily]:
    """광고 지표와 일관되게 GA4 세션 데이터를 파생 생성한다."""
    rng = random.Random(7)
    agg: dict[tuple, Ga4Daily] = {}
    for m in metrics:
        sm = _SOURCE_MEDIUM[Channel(m.channel)]
        key = (m.date, sm)
        row = agg.get(key)
        if row is None:
            row = agg[key] = Ga4Daily(date=m.date, source_medium=sm)
        # 클릭의 85~95%가 세션으로 유입되는 것으로 가정
        sessions = int(m.clicks * rng.uniform(0.85, 0.95))
        row.sessions += sessions
        row.engaged_sessions += int(sessions * rng.uniform(0.45, 0.65))
        row.conversions += m.conversions * rng.uniform(0.9, 1.0)
        row.revenue += m.revenue * rng.uniform(0.9, 1.0)
        row.avg_engagement_seconds = rng.uniform(35, 90)
    # 자연 유입도 약간 섞는다
    dates = sorted({m.date for m in metrics})
    for d in dates:
        organic = Ga4Daily(
            date=d, source_medium="google / organic",
            sessions=int(rng.uniform(700, 1200) * _season(d)),
        )
        organic.engaged_sessions = int(organic.sessions * 0.6)
        organic.conversions = round(organic.sessions * 0.02, 1)
        organic.revenue = round(organic.conversions * 50_000)
        organic.avg_engagement_seconds = rng.uniform(60, 120)
        agg[(d, organic.source_medium)] = organic
    return [r for r in agg.values()]


def generate_clarity(metrics: list[DailyMetric]) -> list[ClarityDaily]:
    rng = random.Random(21)
    by_date: dict[date, int] = {}
    for m in metrics:
        by_date[m.date] = by_date.get(m.date, 0) + m.clicks
    out: list[ClarityDaily] = []
    for d, clicks in sorted(by_date.items()):
        sessions = int(clicks * 0.9 + rng.uniform(700, 1200))
        out.append(ClarityDaily(
            date=d,
            sessions=sessions,
            bot_sessions=int(sessions * rng.uniform(0.02, 0.05)),
            dead_clicks=int(sessions * rng.uniform(0.06, 0.12)),
            rage_clicks=int(sessions * rng.uniform(0.01, 0.04)),
            quick_backs=int(sessions * rng.uniform(0.05, 0.10)),
            excessive_scrolls=int(sessions * rng.uniform(0.02, 0.06)),
            script_errors=int(sessions * rng.uniform(0.005, 0.02)),
            avg_scroll_depth=rng.uniform(48, 68),
        ))
    return out
