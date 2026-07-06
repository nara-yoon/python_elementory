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
from core.models import CampaignSpec, Channel, DailyMetric, LaunchResult
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
