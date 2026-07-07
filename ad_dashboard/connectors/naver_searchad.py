"""네이버 검색광고 API 커넥터.

- 문서: https://naver.github.io/searchad-apidoc/
- 인증: API 라이선스/비밀키 기반 HMAC-SHA256 서명
  (X-Timestamp, X-API-KEY, X-Customer, X-Signature 헤더)
- 필요한 환경변수:
    NAVER_SEARCHAD_API_KEY      : 액세스 라이선스
    NAVER_SEARCHAD_SECRET_KEY   : 비밀키
    NAVER_SEARCHAD_CUSTOMER_ID  : 광고주 Customer ID
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from datetime import date, timedelta

import requests

from core import settings
from core.models import (CampaignSpec, Channel, CreativeSpec, DailyMetric,
                         LaunchResult)
from .base import AdPlatformConnector, ConnectorError

BASE_URL = "https://api.searchad.naver.com"


class NaverSearchAdConnector(AdPlatformConnector):
    channel = Channel.NAVER_SEARCH.value

    def __init__(self) -> None:
        self.api_key = settings.get("NAVER_SEARCHAD_API_KEY")
        self.secret_key = settings.get("NAVER_SEARCHAD_SECRET_KEY")
        self.customer_id = settings.get("NAVER_SEARCHAD_CUSTOMER_ID")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key and self.customer_id)

    # -- 인증 ---------------------------------------------------------------
    def _headers(self, method: str, uri: str) -> dict:
        timestamp = str(round(time.time() * 1000))
        message = f"{timestamp}.{method}.{uri}"
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": self.api_key,
            "X-Customer": self.customer_id,
            "X-Signature": signature,
        }

    def _request(self, method: str, uri: str, *, params: dict | None = None,
                 json: dict | list | None = None):
        resp = requests.request(
            method, BASE_URL + uri, headers=self._headers(method, uri),
            params=params, json=json, timeout=30,
        )
        if resp.status_code >= 400:
            raise ConnectorError(f"네이버 검색광고 API 오류 {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.text else None

    # -- 캠페인 생성 ---------------------------------------------------------
    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        if not self.is_configured():
            return self._not_configured()
        try:
            campaign = self._request("POST", "/ncc/campaigns", json={
                "campaignTp": "WEB_SITE",           # 파워링크
                "name": spec.name,
                "customerId": int(self.customer_id),
                "dailyBudget": spec.daily_budget,
                "useDailyBudget": True,
            })
            campaign_id = campaign["nccCampaignId"]

            # 광고그룹 + 키워드 + 소재까지 한 번에 세팅
            adgroup = self._request("POST", "/ncc/adgroups", json={
                "nccCampaignId": campaign_id,
                "name": f"{spec.name}_그룹1",
                "pcChannelKey": settings.get("NAVER_SEARCHAD_PC_CHANNEL_KEY"),
                "mobileChannelKey": settings.get("NAVER_SEARCHAD_MOBILE_CHANNEL_KEY"),
            })
            adgroup_id = adgroup["nccAdgroupId"]

            if spec.keywords:
                self._request(
                    "POST", "/ncc/keywords",
                    params={"nccAdgroupId": adgroup_id},
                    json=[{"keyword": kw} for kw in spec.keywords[:100]],
                )
            if spec.headline:
                self._request("POST", "/ncc/ads", json={
                    "nccAdgroupId": adgroup_id,
                    "type": "TEXT_45",
                    "ad": {
                        "headline": spec.headline[:15],
                        "description": spec.description[:45],
                        "pc": {"final": spec.landing_url},
                        "mobile": {"final": spec.landing_url},
                    },
                })
            return LaunchResult(channel=self.channel, ok=True, campaign_id=campaign_id,
                                message="캠페인/광고그룹/키워드/소재 생성 완료")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    # -- 소재 변경 -----------------------------------------------------------
    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """캠페인의 모든 광고그룹에 새 텍스트 소재를 등록한다."""
        if not self.is_configured():
            return self._not_configured()
        try:
            adgroups = self._request("GET", "/ncc/adgroups",
                                     params={"nccCampaignId": campaign_id}) or []
            if not adgroups:
                return LaunchResult(channel=self.channel, ok=False,
                                    message="광고그룹이 없습니다")
            for g in adgroups:
                self._request("POST", "/ncc/ads", json={
                    "nccAdgroupId": g["nccAdgroupId"],
                    "type": "TEXT_45",
                    "ad": {
                        "headline": creative.headline[:15],
                        "description": creative.description[:45],
                        "pc": {"final": creative.landing_url},
                        "mobile": {"final": creative.landing_url},
                    },
                })
            return LaunchResult(
                channel=self.channel, ok=True, campaign_id=campaign_id,
                message=f"광고그룹 {len(adgroups)}개에 새 소재 등록 완료 "
                        "(기존 소재는 관리자에서 중지하세요)")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    # -- 성과 수집 -----------------------------------------------------------
    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        if not self.is_configured():
            return []
        campaigns = self._request("GET", "/ncc/campaigns") or []
        out: list[DailyMetric] = []
        for c in campaigns:
            cid, cname = c["nccCampaignId"], c["name"]
            # StatReport 는 하루 단위 조회이므로 일자별로 순회
            day = start
            while day <= end:
                stats = self._request("GET", "/stats", params={
                    "ids": cid,
                    "fields": '["impCnt","clkCnt","salesAmt","ccnt","convAmt"]',
                    "timeRange": (f'{{"since":"{day.isoformat()}",'
                                  f'"until":"{day.isoformat()}"}}'),
                })
                for row in (stats or {}).get("data", []):
                    out.append(DailyMetric(
                        date=day, channel=self.channel,
                        campaign_id=cid, campaign_name=cname,
                        impressions=int(row.get("impCnt", 0)),
                        clicks=int(row.get("clkCnt", 0)),
                        cost=float(row.get("salesAmt", 0)),       # 부가세 제외 비용
                        conversions=float(row.get("ccnt", 0)),
                        revenue=float(row.get("convAmt", 0)),
                    ))
                day += timedelta(days=1)
        return out
