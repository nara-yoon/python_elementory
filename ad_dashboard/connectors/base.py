"""광고 플랫폼 커넥터 공통 인터페이스.

모든 커넥터는 두 가지 일을 한다:
  1. create_campaign(spec)  — 통합 CampaignSpec 을 플랫폼 API 페이로드로 변환해 캠페인 생성
  2. fetch_daily_metrics()  — 기간 내 일자별 성과를 통합 DailyMetric 목록으로 반환

자격증명이 없으면 is_configured() 가 False 를 반환하고,
호출부(collector/launcher)는 해당 채널을 건너뛰거나 데모 데이터로 대체한다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from core.models import CampaignSpec, CreativeSpec, DailyMetric, LaunchResult


class ConnectorError(RuntimeError):
    """플랫폼 API 호출 실패."""


class AdPlatformConnector(ABC):
    """광고 플랫폼 커넥터의 추상 베이스."""

    #: Channel 값 (models.Channel)
    channel: str = ""

    @abstractmethod
    def is_configured(self) -> bool:
        """이 플랫폼의 API 자격증명이 준비되었는지."""

    @abstractmethod
    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        """통합 캠페인 정의로 이 플랫폼에 캠페인을 생성한다."""

    @abstractmethod
    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        """기간 내 일자별 x 캠페인별 성과를 통합 스키마로 반환한다."""

    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """캠페인 하위 광고그룹들에 새 소재를 등록한다(대량 소재 변경용).

        대부분의 플랫폼은 소재 '수정' 대신 새 소재 등록 후 기존 소재를
        중지하는 방식을 권장하므로, 기본 구현은 새 소재 추가다.
        """
        return LaunchResult(channel=self.channel, ok=False,
                            message="이 채널은 소재 변경을 지원하지 않습니다")

    def _not_configured(self) -> LaunchResult:
        return LaunchResult(
            channel=self.channel, ok=False,
            message="API 자격증명이 설정되지 않았습니다 (.env 확인)",
        )
