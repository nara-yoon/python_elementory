"""캠페인 자동 세팅 오케스트레이터.

하나의 CampaignSpec(YAML 또는 대시보드 입력)을 받아 선택된 채널들의
커넥터로 팬아웃해 캠페인을 생성하고, 결과를 DB(campaigns)에 기록한다.
자격증명이 없는 채널은 데모 모드에서는 시뮬레이션으로 처리한다.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from core import storage
from core.models import CampaignSpec, LaunchResult

from .collector import all_connectors

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "campaign_template.yaml"


def load_spec(path: Path | str = CONFIG_PATH) -> CampaignSpec:
    """YAML 템플릿을 CampaignSpec 으로 로드한다."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return CampaignSpec(**raw)


def launch(spec: CampaignSpec, demo: bool = False) -> list[LaunchResult]:
    """spec.channels 에 지정된 채널마다 캠페인을 생성한다.

    demo=True 이거나 해당 채널 자격증명이 없으면 실제 API 를 부르지 않고
    시뮬레이션 결과를 만든다(대시보드 체험용).
    """
    conn = storage.connect()
    results: list[LaunchResult] = []
    connectors = {c.channel: c for c in all_connectors()}

    for channel in spec.channels:
        connector = connectors.get(channel)
        if connector is None:
            results.append(LaunchResult(channel=channel, ok=False,
                                        message=f"알 수 없는 채널: {channel}"))
            continue

        if demo or not connector.is_configured():
            # 시뮬레이션: 이름+채널 해시로 안정적인 가짜 ID 발급
            fake_id = "sim_" + hashlib.md5(
                f"{channel}:{spec.name}".encode()).hexdigest()[:10]
            result = LaunchResult(
                channel=channel, ok=True, campaign_id=fake_id,
                message="(시뮬레이션) 캠페인 생성 — 자격증명 등록 시 실제 API로 생성됩니다")
        else:
            result = connector.create_campaign(spec)

        if result.ok:
            storage.save_campaign(conn, channel, result.campaign_id,
                                  spec.name, spec.daily_budget,
                                  status="SIMULATED" if result.campaign_id.startswith("sim_")
                                  else "PAUSED")
        results.append(result)

    conn.close()
    return results
