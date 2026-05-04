import json
import re
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.views.generic import TemplateView

SYSTEM_PROMPT = """
당신은 '현장이음' 앱의 AI 상담사입니다.
건설 일용직 근로자를 위해 쉽고 친절하게 답변하세요.

답변 원칙:
1. 짧고 쉬운 문장 사용 (한 문장 20자 이내 권장)
2. 어려운 법률/행정 용어는 반드시 쉬운 말로 풀어 설명
3. 단계가 있으면 숫자를 붙여 순서대로 안내
4. 전화번호나 웹사이트는 구체적으로 안내
5. 모르는 내용은 "건설근로자공제회(1588-0075)로 전화하세요"라고 안내
6. 답변은 5줄 이내로 마무리
7. 앱 메뉴명과 다음 행동을 먼저 안내
8. 데이터 예시는 최대 3개만 사용
9. "어르신", "어머니", "아버님" 같은 호칭은 사용하지 않기

주요 답변 영역:
- 퇴직공제 적립금 수령 방법
- 산재 신청 절차
- 무료 건강검진 신청 방법  
- 일자리 찾는 방법
- 현장 안전 주의사항

현장 브리핑 원칙:
- 사용자가 현장명과 지역을 주면 출근 전 브리핑으로 답변
- 퇴직공제 가입현장 확인, 건강검진 자격 확인 방법, 날씨 확인, 응급실/취업지원 연결을 함께 안내
- 산재, 임금체불, 사고, 화학물질은 참고 안내임을 밝히고 119, 고용노동부 1350, 근로복지공단, 현장 안전관리자 확인을 안내
"""

@method_decorator(ensure_csrf_cookie, name="dispatch")
class ChatView(TemplateView):
    template_name = 'chatbot/chat.html'


REGION_KEYWORDS = [
    "서울", "경기", "인천", "강원", "대전", "충남", "충북", "세종",
    "광주", "전남", "전북", "대구", "경북", "부산", "울산", "경남", "제주",
    "수원", "성남", "고양", "용인", "창원", "전주", "천안", "청주",
]


def extract_region(message):
    for region in REGION_KEYWORDS:
        if region in message:
            return region
    return ""


def extract_search_terms(message):
    cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", message)
    stopwords = {
        "퇴직", "공제", "퇴직공제", "가입", "현장", "확인", "조회", "검색",
        "어떻게", "하려면", "알려줘", "있나요", "인가요", "건강", "검진",
        "기관", "취업", "지원", "지사", "센터", "일자리", "무료",
    }
    return [
        token for token in cleaned.split()
        if len(token) >= 2 and token not in stopwords
    ][:3]


def extract_number_after(message, keywords):
    for keyword in keywords:
        pattern = rf"{keyword}\D{{0,8}}(\d+)"
        match = re.search(pattern, message)
        if match:
            return int(match.group(1))
    return None


def extract_labeled_text(message, labels):
    for label in labels:
        pattern = rf"{label}\s*:\s*([^\.。\n]+)"
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip()
    return ""


def build_briefing_reply(user_message):
    from jobs.models import EmploymentSupportCenter
    from pension.models import PensionSite
    from django.db.models import Q

    message = user_message
    if "현장 브리핑" not in message and "출근 브리핑" not in message:
        return ""

    region = extract_region(message) or "선택 지역"
    site_keyword = extract_labeled_text(message, ["현장명 또는 시공사", "현장명", "시공사"])
    terms = extract_search_terms(site_keyword) if site_keyword else []
    site_qs = PensionSite.objects.none()
    for term in terms:
        site_qs = site_qs | PensionSite.objects.filter(
            Q(project_name__icontains=term)
            | Q(company_name__icontains=term)
            | Q(address__icontains=term)
        )
    site = site_qs.distinct().first()

    center_qs = EmploymentSupportCenter.objects.all()
    if region != "선택 지역":
        region_groups = {
            "서울": ["서울", "경기", "인천"],
            "경기": ["서울", "경기", "인천"],
            "인천": ["서울", "경기", "인천"],
            "광주": ["광주", "전남", "전북"],
            "전남": ["광주", "전남", "전북"],
            "전북": ["광주", "전남", "전북"],
            "대전": ["대전", "세종", "충남", "충북"],
            "충남": ["대전", "세종", "충남", "충북"],
            "충북": ["대전", "세종", "충남", "충북"],
            "세종": ["대전", "세종", "충남", "충북"],
            "부산": ["부산", "울산", "경남"],
            "울산": ["부산", "울산", "경남"],
            "경남": ["부산", "울산", "경남"],
            "대구": ["대구", "경북"],
            "경북": ["대구", "경북"],
        }
        keywords = region_groups.get(region, [region])
        q = Q()
        for keyword in keywords:
            q |= Q(region__icontains=keyword) | Q(location__icontains=keyword)
        center_qs = center_qs.filter(q)
    center = center_qs.first()

    health_status = "건설e음 또는 공제회 상담으로 자격을 확인하세요."

    site_line = (
        f"퇴직공제: {site.project_name} 확인 후보가 있어요."
        if site
        else "퇴직공제: 현장명으로 가입현장을 다시 검색하세요."
    )
    center_line = (
        f"취업지원: {center.region} {center.name}, 1666-1829."
        if center
        else "취업지원: 일자리 메뉴에서 권역을 선택하세요."
    )

    return sanitize_reply(
        "오늘의 현장 브리핑입니다.\n"
        f"1. 지역: {region}\n"
        f"2. {site_line}\n"
        f"3. 건강검진: {health_status}\n"
        "4. 날씨: 작업 날씨 메뉴에서 확인하세요. 위치 권한을 허용하면 현재 위치 기준입니다.\n"
        f"5. {center_line}\n"
        "사고·산재는 119, 1350, 현장 안전관리자 확인이 필요합니다."
    )


def build_app_context(user_message):
    from health.models import HealthClinic
    from jobs.models import EmploymentSupportCenter
    from pension.models import PensionSite
    from django.db.models import Q

    message = user_message.lower()
    original_message = user_message
    region = extract_region(original_message)
    terms = extract_search_terms(original_message)
    parts = []

    if "취업" in message or "일자리" in message or "지사" in message or "센터" in message:
        center_qs = EmploymentSupportCenter.objects.all()
        if region:
            center_qs = center_qs.filter(Q(region__icontains=region) | Q(location__icontains=region))
        centers = center_qs[:3]
        names = ", ".join(f"{c.region} {c.name}" for c in centers)
        parts.append(
            "취업지원 안내: "
            "일자리 메뉴에서 지역별 지사를 확인합니다. "
            "대표번호는 1666-1829입니다. "
            f"예시: {names}."
        )

    if "건강" in message or "검진" in message or "병원" in message:
        clinic_qs = HealthClinic.objects.all()
        if region:
            clinic_qs = clinic_qs.filter(Q(address__icontains=region) | Q(region__icontains=region))
        clinics = list(clinic_qs[:3])
        clinic_examples = ", ".join(c.name for c in clinics)
        parts.append(
            "무료 건강검진 안내: "
            "건강·안전 메뉴에서 지역을 선택합니다. "
            "기관명, 주소, 지도 버튼을 볼 수 있습니다. "
            f"{clinic_examples and '예시: ' + clinic_examples}."
        )

    if "퇴직" in message or "공제" in message or "현장" in message or "가입" in message:
        site_qs = PensionSite.objects.none()
        for term in terms:
            site_qs = site_qs | PensionSite.objects.filter(
                Q(project_name__icontains=term) |
                Q(company_name__icontains=term) |
                Q(address__icontains=term)
            )
        sites = list(site_qs.distinct()[:3])
        site_examples = ", ".join(f"{s.project_name}({s.company_name})" for s in sites)
        parts.append(
            "퇴직공제 현장 조회: "
            "퇴직공제 메뉴에서 현장명이나 시공사를 검색합니다. "
            "검색어는 2글자 이상 입력합니다. "
            f"{site_examples and '예시: ' + site_examples}."
        )

    if "날씨" in message or "폭염" in message or "비" in message or "강풍" in message:
        parts.append(
            "기상 작업주의: "
            "기상 작업주의 페이지에서 오늘 작업 날씨를 확인합니다."
        )

    if "응급" in message or "사고" in message or "다쳤" in message or "병원" in message:
        parts.append(
            "긴급 도움: "
            "긴급 도움 메뉴에서 가까운 응급실 3곳을 확인합니다."
        )

    return "\n".join(parts)


def fallback_reply(user_message):
    message = user_message.lower()
    briefing = build_briefing_reply(user_message)
    if briefing:
        return briefing

    context = build_app_context(user_message)

    if "퇴직" in message or "공제" in message:
        return (
            "퇴직공제는 현장 가입 여부가 중요합니다.\n"
            "1. 퇴직공제 메뉴를 여세요.\n"
            "2. 현장명이나 시공사를 검색하세요.\n"
            f"{context and chr(10) + context}"
        )

    if "건강" in message or "검진" in message:
        return (
            "무료 건강검진은 건강·안전 메뉴에서 찾습니다.\n"
            "1. 건강·안전 메뉴를 여세요.\n"
            "2. 지역을 선택하세요.\n"
            f"{context and chr(10) + context}"
        )

    if "일자리" in message or "취업" in message or "센터" in message:
        return (
            "취업지원은 일자리 메뉴에서 확인합니다.\n"
            "1. 일자리 메뉴를 누르세요.\n"
            "2. 지역을 선택하세요.\n"
            f"{context and chr(10) + context}"
        )

    if "안전" in message or "사고" in message or "산재" in message:
        return (
            "사고가 나면 먼저 안전을 확보하세요.\n"
            "1. 안전모와 안전대를 확인하세요.\n"
            "2. 다치면 관리자에게 알리세요.\n"
            "3. 긴급 도움에서 응급실을 찾으세요.\n"
            f"{context and chr(10) + context}"
        )

    return (
        "현장이음에서 바로 확인할 수 있습니다.\n"
        "퇴직공제, 건강검진, 일자리, 안전을 물어보세요.\n"
        "정확한 상담은 건설근로자공제회 1588-0075로 문의하세요.\n"
        f"{context and chr(10) + context}"
    )

def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST만 허용"}, status=405)
    
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
        history_raw = body.get("history", [])
        
        if not user_message:
            return JsonResponse({"error": "메시지를 입력해주세요", "status": "error"}, status=400)

        briefing = build_briefing_reply(user_message)
        if briefing:
            return JsonResponse({"reply": briefing, "status": "ok"})

        if not settings.GEMINI_API_KEY:
            return JsonResponse({"reply": fallback_reply(user_message), "status": "ok"})

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # history format for gemini: [{'role': 'user', 'parts': [{'text': '...'}]}, {'role': 'model', 'parts': [{'text': '...'}]}]
        contents = []
        for msg in history_raw:
            if "role" in msg and "parts" in msg:
                contents.append(types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["parts"][0]["text"])]
                ))
            elif "role" in msg and "content" in msg: # Fallback for old format
                 contents.append(types.Content(
                    role="model" if msg["role"] == "assistant" or msg["role"] == "bot" else "user",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
                
        # Append current message
        app_context = build_app_context(user_message)
        if app_context:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"앱 내부 데이터 참고:\n{app_context}")]
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)]
            )
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.5,
            )
        )
        
        return JsonResponse({"reply": sanitize_reply(response.text), "status": "ok"})
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return JsonResponse({
            "reply": sanitize_reply(fallback_reply(user_message if 'user_message' in locals() else "")),
            "status": "ok"
        })


def sanitize_reply(text):
    replacements = {
        "어르신, ": "",
        "어르신 ": "",
        "어르신": "근로자님",
        "아버님": "근로자님",
        "어머니": "근로자님",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.strip()
