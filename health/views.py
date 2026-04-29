import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

class ClinicMapView(TemplateView):
    template_name = 'health/clinic_map.html'

def clinics_json(request):
    """지도용 종합건강검진 수검기관 (DB 연동)"""
    lat = request.GET.get("lat", 37.5665)
    lon = request.GET.get("lon", 126.9780)
    region = request.GET.get("region", "")
    
    from .models import HealthClinic
    from django.db.models import Q
    
    qs = HealthClinic.objects.all()
    if region:
        qs = qs.filter(Q(address__icontains=region))
    else:
        # 지역 선택이 없을 때는 최대 50개 제한 (지오코딩 부하 방지)
        qs = qs[:50]
    
    clinics = []
    for c in qs:
        clinics.append({
            "name": c.name,
            "address": c.address,
            "phone": c.phone,
            "lat": float(lat), # 프론트에서 주소 변환해야 함
            "lon": float(lon),
        })
    return JsonResponse({"clinics": clinics})

def safety_alerts_json(request):
    """건설재해사례 API (constDsstr01)"""
    api_url = "https://apis.data.go.kr/B552468/constDsstr01"
    params = {
        "serviceKey": settings.KOSHA_API_KEY,
        "pageNo": 1,
        "numOfRows": 3,
        "type": "json",
    }
    
    try:
        # 인증키가 이미 인코딩되어 있거나 특수문자가 포함된 경우 requests의 자동 인코딩이 문제를 일으킬 수 있음
        # 따라서 URL에 직접 쿼리 스트링을 붙여 호출 시도
        url = f"{api_url}?serviceKey={settings.KOSHA_API_KEY}&pageNo=1&numOfRows=3&type=json"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()


        # 응답 구조 유연하게 파싱
        body = data.get('response', data).get('body', data)
        items_wrap = body.get('items', {})

        # items 가 dict 이거나 list 이거나 모두 처리
        if isinstance(items_wrap, dict):
            items = items_wrap.get('item', [])
        elif isinstance(items_wrap, list):
            items = items_wrap
        else:
            items = []

        if isinstance(items, dict):
            items = [items]

        alerts = []
        for c in items[:3]:
            # 필드명이 다를 수 있으므로 여러 키 시도
            title   = c.get('dsstrNm') or c.get('title') or c.get('accident_nm') or '건설재해 주의'
            summary = c.get('dsstrCn')  or c.get('content') or c.get('summary') or ''
            d_type  = c.get('dsstrSe')  or c.get('type')    or c.get('accidentType') or '안전알림'

            alerts.append({
                "title":   title,
                "type":    d_type,
                "summary": str(summary)[:100] + ('…' if len(str(summary)) > 100 else ''),
            })

        if alerts:
            return JsonResponse({"alerts": alerts})
        raise ValueError("빈 응답")

    except Exception as e:
        # API 실패 시 더미 데이터
        dummy_alerts = [
            {"title": "비계 작업 중 추락사고 예방",     "type": "추락", "summary": "안전대 체결을 철저히 하고 작업발판을 확인하세요."},
            {"title": "크레인 인양작업 중 낙하물 주의", "type": "맞음", "summary": "하부 출입을 통제하고 신호수를 배치하세요."},
        ]
        return JsonResponse({"alerts": dummy_alerts})

