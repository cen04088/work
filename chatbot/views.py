import json
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

SYSTEM_PROMPT = """
당신은 '현장이음' 앱의 AI 상담사입니다.
건설 일용직 근로자, 특히 50대 이상 분들을 위해 쉽고 친절하게 답변하세요.

답변 원칙:
1. 짧고 쉬운 문장 사용 (한 문장 20자 이내 권장)
2. 어려운 법률/행정 용어는 반드시 쉬운 말로 풀어 설명
3. 단계가 있으면 숫자를 붙여 순서대로 안내
4. 전화번호나 웹사이트는 구체적으로 안내
5. 모르는 내용은 "건설근로자공제회(1588-0075)로 전화하세요"라고 안내

주요 답변 영역:
- 퇴직공제 적립금 수령 방법
- 산재 신청 절차
- 무료 건강검진 신청 방법  
- 일자리 찾는 방법
- 현장 안전 주의사항
"""

class ChatView(TemplateView):
    template_name = 'chatbot/chat.html'

def fallback_reply(user_message):
    message = user_message.lower()

    if "퇴직" in message or "공제" in message:
        return (
            "퇴직공제는 일한 날마다 쌓입니다.\n"
            "1. 현장 가입 여부를 먼저 확인하세요.\n"
            "2. 건설근로자공제회에 신청하세요.\n"
            "3. 자세한 문의는 1588-0075입니다."
        )

    if "건강" in message or "검진" in message:
        return (
            "건강검진은 공제회 지원 대상이면 무료입니다.\n"
            "1. 건강·안전 메뉴를 여세요.\n"
            "2. 지역을 선택하세요.\n"
            "3. 가까운 기관에 전화하세요."
        )

    if "일자리" in message or "취업" in message or "센터" in message:
        return (
            "일자리는 취업지원센터에서 안내받을 수 있습니다.\n"
            "1. 일자리 메뉴를 누르세요.\n"
            "2. 지역을 선택하세요.\n"
            "3. 센터 전화번호로 문의하세요."
        )

    if "안전" in message or "사고" in message or "산재" in message:
        return (
            "현장에서는 추락과 낙하물을 조심하세요.\n"
            "1. 안전모와 안전대를 확인하세요.\n"
            "2. 작업 전 발판을 확인하세요.\n"
            "3. 다치면 바로 관리자에게 알리세요."
        )

    return (
        "현장이음은 건설근로자를 돕는 서비스입니다.\n"
        "퇴직공제, 건강검진, 일자리, 안전을 물어보세요.\n"
        "정확한 상담은 건설근로자공제회 1588-0075로 문의하세요."
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
        
        return JsonResponse({"reply": response.text, "status": "ok"})
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return JsonResponse({
            "reply": fallback_reply(user_message if 'user_message' in locals() else ""),
            "status": "ok"
        })
