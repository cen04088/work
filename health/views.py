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
    """한국산업안전보건공단 국내재해사례 (API 연동)"""
    api_url = "https://apis.data.go.kr/B552468/disaster_api02"
    params = {
        "serviceKey": settings.KOSHA_API_KEY,
        "pageNo": 1,
        "numOfRows": 3,
        "type": "json",
    }
    
    try:
        res = requests.get(api_url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if isinstance(items, dict):
            items = [items]
            
        alerts = []
        for c in items:
            alerts.append({
                "title": c.get('title', '안전사고 주의'),
                "type": "안전알림",
                "summary": c.get('content', '')[:100] + "...",
            })
        return JsonResponse({"alerts": alerts})
    except Exception as e:
        # API 실패 시 더미 데이터
        dummy_alerts = [
            {"title": "비계 작업 중 추락사고 예방", "type": "추락", "summary": "안전대 체결을 철저히 하고 작업발판을 확인하세요."},
            {"title": "크레인 인양작업 중 낙하물 주의", "type": "맞음", "summary": "하부 출입을 통제하고 신호수를 배치하세요."},
        ]
        return JsonResponse({"alerts": dummy_alerts})
