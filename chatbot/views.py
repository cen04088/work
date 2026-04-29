import json
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView
from google import genai
from google.genai import types

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

def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST만 허용"}, status=405)
    
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
        history_raw = body.get("history", [])
        
        if not user_message:
            return JsonResponse({"error": "메시지를 입력해주세요", "status": "error"}, status=400)
            
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
            "reply": "죄송합니다. 잠시 후 다시 시도해주세요.\n📞 직접 문의: 건설근로자공제회 1588-0075",
            "status": "error"
        })
