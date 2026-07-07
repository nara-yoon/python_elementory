"""카카오 키워드광고(검색광고) API 커넥터.

- 문서: https://developers.kakao.com (키워드광고 API)
- 인증: 카카오 OAuth2 액세스 토큰 + 광고계정 ID 헤더
- 필요한 환경변수:
    KAKAO_ACCESS_TOKEN        : OAuth2 액세스 토큰
    KAKAO_KEYWORD_AD_ACCOUNT  : 키워드광고 계정 ID (adAccountId)
"""
from __future__ import annotations

from datetime import date

import requests

from core import settings
from core.models import (CampaignSpec, Channel, CreativeSpec, DailyMetric,
                         HourlyMetric, LaunchResult)
from .base import AdPlatformConnector, ConnectorError

BASE_URL = "https://apis.moment.kakao.com/keywordad"


class KakaoKeywordConnector(AdPlatformConnector):
    channel = Channel.KAKAO_SEARCH.value

    def __init__(self) -> None:
        self.access_token = settings.get("KAKAO_ACCESS_TOKEN")
        self.ad_account_id = settings.get("KAKAO_KEYWORD_AD_ACCOUNT")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.ad_account_id)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "adAccountId": self.ad_account_id,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs):
        resp = requests.request(method, BASE_URL + path, headers=self._headers(),
                                timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise ConnectorError(f"카카오 키워드광고 API 오류 {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.text else None

    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        if not self.is_configured():
            return self._not_configured()
        try:
            campaign = self._request("POST", "/openapi/v1/campaigns", json={
                "name": spec.name,
                "dailyBudgetAmount": spec.daily_budget,
            })
            campaign_id = str(campaign["id"])

            adgroup = self._request("POST", "/openapi/v1/adGroups", json={
                "campaignId": campaign_id,
                "name": f"{spec.name}_그룹1",
                "dailyBudgetAmount": spec.daily_budget,
                "bidAmount": 300,      # 기본 입찰가(원). 세팅 후 관리자에서 조정
            })
            adgroup_id = str(adgroup["id"])

            if spec.keywords:
                self._request("POST", "/openapi/v1/keywords", json=[
                    {"adGroupId": adgroup_id, "text": kw} for kw in spec.keywords[:100]
                ])
            if spec.headline:
                self._request("POST", "/openapi/v1/creatives", json={
                    "adGroupId": adgroup_id,
                    "title": spec.headline,
                    "description": spec.description,
                    "landingUrl": spec.landing_url,
                })
            return LaunchResult(channel=self.channel, ok=True, campaign_id=campaign_id,
                                message="캠페인/그룹/키워드/소재 생성 완료")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """캠페인의 모든 광고그룹에 새 소재를 등록한다."""
        if not self.is_configured():
            return self._not_configured()
        try:
            adgroups = self._request("GET", "/openapi/v1/adGroups",
                                     params={"campaignId": campaign_id}) or []
            if isinstance(adgroups, dict):
                adgroups = adgroups.get("content", [])
            if not adgroups:
                return LaunchResult(channel=self.channel, ok=False,
                                    message="광고그룹이 없습니다")
            for g in adgroups:
                self._request("POST", "/openapi/v1/creatives", json={
                    "adGroupId": str(g["id"]),
                    "title": creative.headline,
                    "description": creative.description,
                    "landingUrl": creative.landing_url,
                })
            return LaunchResult(
                channel=self.channel, ok=True, campaign_id=campaign_id,
                message=f"광고그룹 {len(adgroups)}개에 새 소재 등록 완료")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        if not self.is_configured():
            return []
        campaigns = self._request("GET", "/openapi/v1/campaigns") or []
        if isinstance(campaigns, dict):
            campaigns = campaigns.get("content", [])
        out: list[DailyMetric] = []
        for c in campaigns:
            cid, cname = str(c["id"]), c.get("name", "")
            report = self._request("GET", "/openapi/v1/report/campaigns", params={
                "campaignId": cid,
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "timeUnit": "DAY",
                "metricsGroups": "BASIC,CONVERSION",
            })
            for row in (report or {}).get("data", []):
                metrics = row.get("metrics", {})
                out.append(DailyMetric(
                    date=date.fromisoformat(str(row["start"])[:10]),
                    channel=self.channel, campaign_id=cid, campaign_name=cname,
                    impressions=int(metrics.get("imp", 0)),
                    clicks=int(metrics.get("click", 0)),
                    cost=float(metrics.get("spending", 0)),
                    conversions=float(metrics.get("convPurchase1d", 0)),
                    revenue=float(metrics.get("convPurchaseP1d", 0)),
                ))
        return out

    def fetch_hourly_metrics(self, start: date, end: date) -> list[HourlyMetric]:
        """timeUnit=HOUR 로 시간대별 성과를 가져와 채널 합계로 반환한다."""
        if not self.is_configured():
            return []
        campaigns = self._request("GET", "/openapi/v1/campaigns") or []
        if isinstance(campaigns, dict):
            campaigns = campaigns.get("content", [])
        agg: dict[tuple, HourlyMetric] = {}
        for c in campaigns:
            report = self._request("GET", "/openapi/v1/report/campaigns", params={
                "campaignId": str(c["id"]),
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "timeUnit": "HOUR",
                "metricsGroups": "BASIC,CONVERSION",
            })
            for row in (report or {}).get("data", []):
                s = str(row.get("start", ""))          # YYYYMMDDHH
                if len(s) < 10:
                    continue
                day = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
                hour = int(s[8:10])
                metrics = row.get("metrics", {})
                m = agg.get((day, hour))
                if m is None:
                    m = agg[(day, hour)] = HourlyMetric(
                        date=day, hour=hour, channel=self.channel)
                m.impressions += int(metrics.get("imp", 0))
                m.clicks += int(metrics.get("click", 0))
                m.cost += float(metrics.get("spending", 0))
                m.conversions += float(metrics.get("convPurchase1d", 0))
                m.revenue += float(metrics.get("convPurchaseP1d", 0))
        return list(agg.values())
