"""통합 광고 대시보드 CLI.

사용법:
  python cli.py collect [--days 30] [--demo]   성과 데이터 수집(적재)
  python cli.py launch  [--config PATH] [--demo]  캠페인 자동 세팅
  python cli.py dashboard                      대시보드 실행 안내
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import campaign_launcher, collector
from core.models import CHANNEL_LABELS


def cmd_collect(args: argparse.Namespace) -> None:
    counts = collector.collect(days=args.days, demo=args.demo)
    print("수집 결과:")
    for key, n in counts.items():
        label = CHANNEL_LABELS.get(key, key)
        print(f"  {label:<14} {'미설정(건너뜀)' if n == -1 else f'{n:,}건 적재'}")


def cmd_launch(args: argparse.Namespace) -> None:
    spec = campaign_launcher.load_spec(args.config)
    print(f"캠페인 '{spec.name}' 세팅 시작 — 채널 {len(spec.channels)}개")
    results = campaign_launcher.launch(spec, demo=args.demo)
    for r in results:
        status = "OK" if r.ok else "실패"
        label = CHANNEL_LABELS.get(r.channel, r.channel)
        print(f"  [{status}] {label:<10} id={r.campaign_id or '-'}  {r.message}")


def cmd_dashboard(_: argparse.Namespace) -> None:
    print("대시보드 실행:")
    print("  streamlit run app.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="통합 광고 대시보드 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="성과 데이터 수집")
    p_collect.add_argument("--days", type=int, default=30)
    p_collect.add_argument("--demo", action="store_true",
                           help="자격증명 없이 데모 데이터 생성")
    p_collect.set_defaults(func=cmd_collect)

    p_launch = sub.add_parser("launch", help="캠페인 자동 세팅")
    p_launch.add_argument("--config", default=str(campaign_launcher.CONFIG_PATH))
    p_launch.add_argument("--demo", action="store_true",
                          help="실제 API 호출 없이 시뮬레이션")
    p_launch.set_defaults(func=cmd_launch)

    p_dash = sub.add_parser("dashboard", help="대시보드 실행 안내")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
