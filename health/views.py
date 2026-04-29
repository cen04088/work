import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
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

def _normalize_disaster_items(data):
    body = data.get("response", data).get("body", {})
    items_wrap = body.get("items", {})

    if isinstance(items_wrap, dict):
        items = items_wrap.get("item", [])
    elif isinstance(items_wrap, list):
        items = items_wrap
    else:
        items = []

    if isinstance(items, dict):
        items = [items]

    return body, items


def _format_disaster_alert(item):
    disaster_type = item.get("dsstrKndNm") or "안전알림"
    process = item.get("jobPrcsNm") or item.get("dtlJobPrcsNm") or "건설 작업"
    detail = item.get("dsstrDtlCn") or ""
    prevention = item.get("rsknsDcrsMsrsCn") or ""

    summary_parts = [detail.strip(), prevention.strip()]
    summary = " ".join(part for part in summary_parts if part)

    return {
        "title": f"{process} 중 {disaster_type} 주의",
        "type": disaster_type,
        "summary": summary[:140] + ("..." if len(summary) > 140 else ""),
        "work": item.get("dtlJobPrcsNm") or process,
        "object": item.get("ocmtNm") or "",
    }


def _fetch_disaster_alerts(dsstr_dy):
    api_url = "http://apis.data.go.kr/B552468/constDsstr01/getconstDsstr01"
    params = {
        "serviceKey": settings.KOSHA_API_KEY,
        "dsstrDy": dsstr_dy,
        "callApiId": "1010",
        "pageNo": "1",
        "numOfRows": "3",
        "type": "json",
    }

    response = requests.get(api_url, params=params, timeout=8)
    response.raise_for_status()
    data = response.json()
    body, items = _normalize_disaster_items(data)

    return {
        "source": "KOSHA_CONSTRUCTION_DAILY_MAJOR_ACCIDENTS",
        "source_date": str(body.get("dsstrDy") or dsstr_dy),
        "total_count": int(body.get("totalCount") or len(items)),
        "alerts": [_format_disaster_alert(item) for item in items[:3]],
    }


def safety_alerts_json(request):
    """한국산업안전보건공단 건설업 일별 중대재해 현황 API."""
    if not settings.KOSHA_API_KEY:
        return JsonResponse({"alerts": [], "error": "KOSHA_API_KEY is not configured"}, status=503)

    today = timezone.localdate()
    requested_date = request.GET.get("date", "").strip()
    if requested_date.isdigit() and len(requested_date) == 8:
        candidate_dates = [requested_date]
    else:
        # API 원천 데이터는 2017~2021년 사고 사례라 오늘과 같은 월/일의 과거 사례를 먼저 찾는다.
        candidate_dates = [f"{year}{today:%m%d}" for year in range(2021, 2016, -1)]
        candidate_dates.append("20210104")

    cache_key = "safety_alerts:" + ":".join(candidate_dates)
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    last_error = None
    for dsstr_dy in candidate_dates:
        try:
            payload = _fetch_disaster_alerts(dsstr_dy)
            if payload["alerts"]:
                payload["is_live_api"] = True
                cache.set(cache_key, payload, 60 * 60)
                return JsonResponse(payload)
        except Exception as exc:
            last_error = str(exc)

    return JsonResponse({
        "alerts": [],
        "is_live_api": False,
        "error": last_error or "No disaster alerts returned from API",
    }, status=502)
