# -*- coding: utf-8 -*-
"""산업군 카테고리별 톤 프리셋.

각 프리셋은 원고 생성기(LLM/템플릿)와 서식기(formatter)가 함께 사용한다.
- voice        : 문체 설명 (LLM 프롬프트에 그대로 들어감)
- ending       : 대표 어미 스타일
- emoji        : 이모지 사용 수준 (none / light / rich)
- highlight    : 형광펜 기본 색상 (HEX)
- greeting     : 도입부 인사 예시
- closing      : 마무리 문장 예시
- section_hints: 소제목 구성 힌트
"""

TONE_PRESETS = {
    "it_tech": {
        "label": "IT / 테크",
        "voice": "논리적이고 신뢰감 있는 전문가 톤. 기술 용어는 쉽게 풀어 설명하고, 근거와 수치를 제시한다.",
        "ending": "~합니다 / ~인데요",
        "emoji": "light",
        "highlight": "#FFF3B0",
        "greeting": "요즘 {keyword}에 대한 관심이 정말 뜨겁죠. 오늘은 실제로 도움이 되는 정보만 정리해 봤습니다.",
        "closing": "오늘 정리한 내용이 {keyword} 선택에 도움이 되셨길 바랍니다. 궁금한 점은 댓글로 남겨주세요!",
        "section_hints": ["개념과 핵심 원리", "장단점 비교", "실전 활용 팁", "선택 가이드"],
    },
    "beauty": {
        "label": "뷰티 / 화장품",
        "voice": "친근하고 발랄한 언니/친구 톤. 사용감 묘사가 풍부하고 공감 표현이 많다.",
        "ending": "~해요 / ~더라구요",
        "emoji": "rich",
        "highlight": "#FFD6E8",
        "greeting": "안녕하세요 여러분~ 오늘은 요즘 제가 푹 빠져있는 {keyword} 이야기를 들고 왔어요 💕",
        "closing": "오늘 소개해드린 {keyword}, 여러분도 꼭 한번 경험해 보세요! 다음에 더 좋은 정보로 돌아올게요 🥰",
        "section_hints": ["첫인상과 패키지", "제형과 사용감", "비포 애프터", "이런 분께 추천"],
    },
    "food": {
        "label": "음식 / 맛집",
        "voice": "생생하고 군침 도는 미식가 톤. 맛과 식감, 분위기 묘사가 구체적이다.",
        "ending": "~해요 / ~답니다",
        "emoji": "rich",
        "highlight": "#FFE5B4",
        "greeting": "오늘은 미루고 미루다 드디어 다녀온 {keyword} 후기를 풀어보려고 해요 🍽️",
        "closing": "{keyword}, 정말 후회 없는 선택이었어요. 근처 가시면 꼭 들러보세요!",
        "section_hints": ["위치와 분위기", "대표 메뉴", "맛 상세 후기", "꿀팁과 총평"],
    },
    "health": {
        "label": "건강 / 의료",
        "voice": "차분하고 신뢰감 있는 전문 상담 톤. 과장 없이 정확한 정보를 전달하고 주의사항을 꼭 짚는다.",
        "ending": "~합니다 / ~하는 것이 좋습니다",
        "emoji": "none",
        "highlight": "#D6F5D6",
        "greeting": "{keyword} 때문에 고민이신 분들이 많습니다. 오늘은 꼭 알아두셔야 할 핵심 정보를 정리했습니다.",
        "closing": "무엇보다 개인차가 있으므로, 정확한 진단은 전문의와 상담하시길 권합니다.",
        "section_hints": ["원인과 증상", "관리 방법", "생활 습관 개선", "주의해야 할 점"],
    },
    "realestate": {
        "label": "부동산 / 재테크",
        "voice": "냉철하고 분석적인 컨설턴트 톤. 데이터와 시장 흐름을 근거로 설명한다.",
        "ending": "~입니다 / ~로 보입니다",
        "emoji": "none",
        "highlight": "#D6E4FF",
        "greeting": "최근 {keyword} 관련 문의가 부쩍 늘었습니다. 시장 상황과 함께 핵심만 짚어보겠습니다.",
        "closing": "투자 판단의 책임은 본인에게 있으며, 본 글은 참고 자료로 활용해 주시기 바랍니다.",
        "section_hints": ["시장 현황", "핵심 체크포인트", "리스크 분석", "전망과 전략"],
    },
    "education": {
        "label": "교육 / 학습",
        "voice": "따뜻하고 격려하는 멘토 톤. 단계별로 차근차근 설명한다.",
        "ending": "~해요 / ~하면 됩니다",
        "emoji": "light",
        "highlight": "#FFF3B0",
        "greeting": "{keyword}, 어디서부터 시작해야 할지 막막하셨죠? 오늘은 단계별로 쉽게 알려드릴게요.",
        "closing": "꾸준함이 가장 큰 무기입니다. 오늘 소개한 방법으로 {keyword} 목표를 꼭 이루시길 응원할게요!",
        "section_hints": ["시작 전 준비", "단계별 학습법", "흔한 실수와 해결법", "추천 자료"],
    },
    "travel": {
        "label": "여행 / 레저",
        "voice": "설레고 감성적인 여행자 톤. 현장감 있는 묘사와 실용 정보를 함께 담는다.",
        "ending": "~였어요 / ~해보세요",
        "emoji": "rich",
        "highlight": "#CFF0F5",
        "greeting": "드디어 다녀왔습니다! 오늘은 {keyword} 여행의 모든 것을 기록해 볼게요 ✈️",
        "closing": "{keyword}에서의 시간, 오래도록 기억에 남을 것 같아요. 여러분의 여행도 응원합니다!",
        "section_hints": ["가는 방법과 일정", "꼭 가봐야 할 곳", "먹거리와 숙소", "여행 꿀팁 정리"],
    },
    "fashion": {
        "label": "패션 / 스타일",
        "voice": "감각적이고 트렌디한 에디터 톤. 스타일링 제안이 구체적이다.",
        "ending": "~해요 / ~죠",
        "emoji": "light",
        "highlight": "#EBD6FF",
        "greeting": "이번 시즌 {keyword}, 놓치면 아쉬운 스타일링 포인트를 모아봤어요.",
        "closing": "나만의 스타일로 소화하는 게 가장 중요하죠. {keyword}로 멋진 하루 보내세요!",
        "section_hints": ["트렌드 분석", "스타일링 제안", "아이템 추천", "코디 주의점"],
    },
    "finance": {
        "label": "금융 / 보험",
        "voice": "꼼꼼하고 객관적인 재무 설계사 톤. 조건과 숫자를 정확히 비교한다.",
        "ending": "~입니다 / ~하시기 바랍니다",
        "emoji": "none",
        "highlight": "#D6E4FF",
        "greeting": "{keyword}, 알아보면 알아볼수록 복잡하게 느껴지실 텐데요. 핵심 조건만 비교해 정리했습니다.",
        "closing": "가입 전 약관을 반드시 확인하시고, 본인의 상황에 맞는 선택을 하시기 바랍니다.",
        "section_hints": ["기본 개념 정리", "조건 비교", "가입 전 체크리스트", "자주 묻는 질문"],
    },
    "interior": {
        "label": "인테리어 / 리빙",
        "voice": "아늑하고 세심한 라이프스타일 톤. 공간의 변화와 실용성을 함께 이야기한다.",
        "ending": "~해요 / ~했답니다",
        "emoji": "light",
        "highlight": "#FFE5B4",
        "greeting": "집 분위기를 바꾸고 싶을 때, {keyword}만큼 효과적인 방법도 없죠. 오늘은 그 과정을 공유해요.",
        "closing": "작은 변화가 일상의 만족을 크게 바꿔줍니다. 여러분의 공간도 응원할게요!",
        "section_hints": ["비포 상황", "선택 기준", "시공/배치 과정", "애프터와 만족도"],
    },
    "parenting": {
        "label": "육아 / 키즈",
        "voice": "다정하고 공감 가득한 부모 톤. 경험담 중심으로 현실적인 팁을 나눈다.",
        "ending": "~해요 / ~하더라고요",
        "emoji": "rich",
        "highlight": "#FFD6E8",
        "greeting": "육아하면서 {keyword} 고민, 안 해본 분 없으시죠? 저희 집 경험을 솔직하게 나눠볼게요.",
        "closing": "모든 아이가 다르니, 우리 아이에게 맞는 방법을 찾아가시길 바라요. 오늘도 육아 파이팅! 💪",
        "section_hints": ["우리 집 상황", "시도해 본 방법", "효과와 아이 반응", "현실 꿀팁"],
    },
    "auto": {
        "label": "자동차 / 모빌리티",
        "voice": "디테일에 강한 마니아 톤. 스펙과 주행 감성을 균형 있게 다룬다.",
        "ending": "~합니다 / ~네요",
        "emoji": "light",
        "highlight": "#D6E4FF",
        "greeting": "오늘 다뤄볼 주제는 많은 분들이 기다리셨던 {keyword}입니다.",
        "closing": "차는 직접 타봐야 안다고 하죠. {keyword} 고민 중이시라면 시승부터 해보시길 추천합니다.",
        "section_hints": ["디자인과 첫인상", "성능과 스펙", "실주행 느낌", "가성비 총평"],
    },
}

DEFAULT_CATEGORY = "it_tech"


def get_preset(category: str) -> dict:
    return TONE_PRESETS.get(category, TONE_PRESETS[DEFAULT_CATEGORY])


def list_categories() -> list:
    return [{"id": key, "label": value["label"]} for key, value in TONE_PRESETS.items()]
