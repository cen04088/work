import html
import re
import requests
from math import atan2, cos, radians, sin, sqrt
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView
from xml.etree import ElementTree

class ClinicMapView(TemplateView):
    template_name = 'health/clinic_map.html'


class WeatherNoticeView(TemplateView):
    template_name = 'health/weather.html'


class SafetyDashboardView(TemplateView):
    template_name = 'health/safety.html'


class EmergencyHelpView(TemplateView):
    template_name = 'health/emergency_help.html'


class MsdsAssistView(TemplateView):
    template_name = 'health/msds_assist.html'

def clinics_json(request):
    """지도용 종합건강검진 수검기관 (DB 연동)"""
    lat = request.GET.get("lat", 37.5665)
    lon = request.GET.get("lon", 126.9780)
    region = request.GET.get("region", "")
    
    from .models import HealthClinic
    from django.db.models import Q
    
    region_groups = {
        "수도권": ["수도권", "서울", "경기", "인천"],
        "강원권": ["강원권", "강원"],
        "충청권": ["충남권", "충북권", "대전", "세종", "충남", "충북", "충청"],
        "호남권": ["전남권", "전북권", "광주", "전남", "전북", "호남"],
        "대구·경북권": ["경북권", "대구", "경북"],
        "부산·울산·경남권": ["경남권", "부산", "울산", "경남"],
        "제주권": ["제주권", "제주"],
    }

    qs = HealthClinic.objects.all()
    if region:
        keywords = region_groups.get(region, [region])
        query = Q()
        for keyword in keywords:
            query |= Q(region__icontains=keyword) | Q(address__icontains=keyword)
        qs = qs.filter(query)
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


def safety_workplaces_json(request):
    """위험성평가 결과 우수사업장 현황 검색."""
    from django.db.models import Q
    from .models import SafetyExcellentWorkplace

    query = (request.GET.get("q") or "").strip()
    labor_office = (request.GET.get("office") or "").strip()
    qs = SafetyExcellentWorkplace.objects.all()

    if query:
        qs = qs.filter(
            Q(workplace_name__icontains=query)
            | Q(construction_site_name__icontains=query)
            | Q(labor_office__icontains=query)
        )
    if labor_office:
        qs = qs.filter(labor_office__icontains=labor_office)

    total_count = SafetyExcellentWorkplace.objects.count()
    results = [
        {
            "workplace_name": item.workplace_name,
            "construction_site_name": item.construction_site_name,
            "labor_office": item.labor_office,
            "recognized_date": item.recognized_date,
        }
        for item in qs[:20]
    ]

    return JsonResponse({
        "results": results,
        "count": len(results),
        "total_count": total_count,
        "is_live_api": False,
        "source": "한국산업안전보건공단_위험성평가 결과 우수사업장 현황",
    })


def msds_search_json(request):
    """KOSHA 물질안전보건자료 목록 검색."""
    keyword = (request.GET.get("q") or "").strip()
    search_type = (request.GET.get("type") or "0").strip()
    if len(keyword) < 2:
        return JsonResponse({"results": [], "error": "검색어를 2글자 이상 입력해주세요."}, status=400)

    api_key = getattr(settings, "MSDS_API_KEY", "") or _public_data_key("kosha")
    if not api_key:
        return _api_error("MSDS_API_KEY 또는 PUBLIC_DATA_API_KEY가 필요합니다.", 503)

    cache_key = f"msds:{search_type}:{keyword}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        response = requests.get(
            "https://apis.data.go.kr/B552468/msdschem/getChemList",
            params={
                "serviceKey": api_key,
                "searchWrd": keyword,
                "searchCnd": search_type,
                "numOfRows": "10",
                "pageNo": "1",
            },
            timeout=8,
        )
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        result_code = root.findtext(".//resultCode", "")
        result_msg = root.findtext(".//resultMsg", "")
        if result_code and result_code != "00":
            return _api_error(result_msg or "MSDS API 응답 오류")

        results = []
        for item in root.findall(".//item"):
            name = _display_msds_name(item.findtext("chemNameKor", ""))
            original_name = _clean_msds_text(item.findtext("chemNameKor", ""))
            match_note = ""
            if search_type == "0" and keyword not in name and keyword in original_name:
                match_note = "검색어가 관용명이나 영문명에서 발견된 결과입니다. 라벨의 제품명·성분명과 맞는지 한 번 더 확인하세요."
            results.append({
                "chem_id": item.findtext("chemId", ""),
                "name": name,
                "original_name": original_name,
                "match_note": match_note,
                "cas_no": item.findtext("casNo", ""),
                "ke_no": item.findtext("keNo", ""),
                "en_no": item.findtext("enNo", ""),
                "un_no": item.findtext("unNo", ""),
                "last_date": item.findtext("lastDate", "")[:10],
            })

        payload = {
            "results": results,
            "count": len(results),
            "is_live_api": True,
            "source": "한국산업안전보건공단_물질안전보건자료",
            "official_url": "https://msds.kosha.or.kr/MSDSInfo/kcic/msdssearchMsds.do",
        }
        cache.set(cache_key, payload, 60 * 60)
        return JsonResponse(payload)
    except Exception as exc:
        return _api_error(_safe_api_error("MSDS", exc))


MSDS_DETAIL_SECTIONS = {
    "02": {
        "title": "얼마나 위험한가요?",
        "description": "라벨에서 먼저 볼 위험 표시만 짧게 정리했어요.",
        "labels": ("신호어", "유해·위험문구", "유해성·위험성 분류"),
        "max_items": 3,
        "max_lines": 3,
    },
    "04": {
        "title": "몸에 닿았을 때",
        "description": "눈, 피부, 흡입처럼 바로 조치가 필요한 상황입니다.",
        "labels": ("눈에 들어갔을 때", "피부에 접촉했을 때", "흡입했을 때", "먹었을 때"),
        "max_items": 4,
        "max_lines": 3,
    },
    "05": {
        "title": "불이 났을 때",
        "description": "불꽃이나 전기공구 사용 전 확인하세요.",
        "labels": ("적절한 소화제", "화학물질로부터 생기는 특정 유해성", "화재진압 시 착용할 보호구 및 예방조치"),
        "max_items": 3,
        "max_lines": 3,
    },
    "06": {
        "title": "새거나 쏟아졌을 때",
        "description": "가까이 가기 전, 치우기 전 먼저 볼 내용입니다.",
        "labels": ("인체를 보호하기 위해 필요한 조치사항 및 보호구", "환경을 보호하기 위해 필요한 조치사항", "정화 또는 제거 방법"),
        "max_items": 3,
        "max_lines": 3,
    },
    "08": {
        "title": "무엇을 착용해야 하나요?",
        "description": "마스크, 장갑, 보안경처럼 필요한 보호구입니다.",
        "labels": ("호흡기 보호", "눈 보호", "손 보호", "신체 보호"),
        "max_items": 4,
        "max_lines": 2,
    },
}


def msds_detail_json(request):
    """KOSHA 물질안전보건자료 상세 항목을 현장용으로 묶어 제공."""
    chem_id = (request.GET.get("chem_id") or "").strip()
    if not chem_id:
        return JsonResponse({"sections": [], "error": "화학물질 번호가 필요합니다."}, status=400)

    api_key = getattr(settings, "MSDS_API_KEY", "") or _public_data_key("kosha")
    if not api_key:
        return JsonResponse({"sections": [], "error": "MSDS_API_KEY 또는 PUBLIC_DATA_API_KEY가 필요합니다."}, status=503)

    cache_key = f"msds-detail:{chem_id}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        sections = []
        for detail_no, meta in MSDS_DETAIL_SECTIONS.items():
            items = _fetch_msds_detail_items(api_key, chem_id, detail_no)
            section_items = _shape_msds_section_items(
                items,
                meta["labels"],
                meta.get("max_items", 4),
                meta.get("max_lines", 3),
            )
            if section_items:
                sections.append({
                    "key": detail_no,
                    "title": meta["title"],
                    "description": meta["description"],
                    "items": section_items,
                })

        payload = {
            "chem_id": chem_id,
            "sections": sections,
            "count": len(sections),
            "is_live_api": True,
            "source": "한국산업안전보건공단_물질안전보건자료",
            "official_url": "https://msds.kosha.or.kr/MSDSInfo/kcic/msdssearchMsds.do",
        }
        cache.set(cache_key, payload, 60 * 60 * 24)
        return JsonResponse(payload)
    except Exception as exc:
        return JsonResponse({"sections": [], "error": _safe_api_error("MSDS 상세", exc)}, status=502)


def _fetch_msds_detail_items(api_key, chem_id, detail_no):
    response = requests.get(
        f"https://apis.data.go.kr/B552468/msdschem/getChemDetail{detail_no}",
        params={
            "serviceKey": api_key,
            "chemId": chem_id,
            "numOfRows": "100",
            "pageNo": "1",
        },
        timeout=8,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    result_code = root.findtext(".//resultCode", "")
    result_msg = root.findtext(".//resultMsg", "")
    if result_code and result_code != "00":
        raise ValueError(result_msg or f"MSDS 상세 {detail_no} 응답 오류")
    return _xml_items(response.text)


def _shape_msds_section_items(items, preferred_labels, max_items=4, max_lines=3):
    by_label = {
        _clean_msds_text(item.get("msdsItemNameKor")): item
        for item in items
        if _clean_msds_text(item.get("msdsItemNameKor"))
    }
    ordered = []
    for label in preferred_labels:
        if label in by_label:
            ordered.append(by_label[label])
    if len(ordered) < 4:
        ordered.extend(item for item in items if item not in ordered)

    shaped = []
    for item in ordered:
        label = _clean_msds_text(item.get("msdsItemNameKor"))
        lines = _split_msds_detail(item.get("itemDetail"))
        if not label or not lines:
            continue
        shaped.append({"label": _easy_msds_label(label), "lines": lines[:max_lines]})
        if len(shaped) >= max_items:
            break
    return shaped


def _split_msds_detail(value):
    lines = []
    for raw_line in str(value or "").replace("\r", "\n").split("|"):
        line = _easy_msds_line(raw_line)
        if not line or line in ("자료없음", "해당없음", "없음"):
            continue
        if _is_low_value_msds_line(line):
            continue
        if len(line) > 86:
            line = line[:83].rstrip() + "..."
        lines.append(line)
    return lines


def _clean_msds_text(value):
    text = html.unescape(html.unescape(str(value or "")))
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_msds_name(value):
    text = _clean_msds_text(value)
    text = re.sub(r"\(\s*관용명\s*:.*$", "", text).strip()
    korean_head = re.match(r"^([가-힣0-9·,\-\s]+)", text)
    if korean_head and korean_head.group(1).strip():
        return korean_head.group(1).strip()
    return text


def _easy_msds_label(label):
    return {
        "유해·위험문구": "주의할 점",
        "유해성·위험성 분류": "위험 종류",
        "인체를 보호하기 위해 필요한 조치사항 및 보호구": "사람을 먼저 보호",
        "환경을 보호하기 위해 필요한 조치사항": "하수구·물길 주의",
        "정화 또는 제거 방법": "치우는 방법",
        "적절한(부적절한) 소화제": "불 끌 때",
        "화재진압 시 착용할 보호구 및 예방조치": "불 끌 때 주의",
        "화학물질로부터 생기는 특정 유해성": "불이 나면 생길 위험",
    }.get(label, label)


def _easy_msds_line(value):
    line = _clean_msds_text(value)
    line = re.sub(r"^[HP]\d{3}(?:\+[HP]\d{3})*\s*:\s*", "", line)

    easy_patterns = (
        ("격리식 전면형 방독마스크", "유기용제용 방독마스크처럼 물질에 맞는 호흡 보호구를 착용하세요."),
        ("산소가 부족한 경우", "산소가 부족한 곳은 들어가지 말고, 송기마스크나 공기호흡기가 필요합니다."),
        ("눈의 자극을 일으키거나", "보안경이나 통기성 보안경을 착용하세요."),
        ("근로자가 접근이 용이한 위치에 긴급세척시설", "가까운 곳에 세안설비나 비상 샤워가 있는지 확인하세요."),
        ("엎질러진 것을 즉시 닦아내고", "보호구를 착용한 뒤 흘린 물질을 정리하세요."),
        ("적절한 보호의를 착용하지 않고", "보호복 없이 새는 용기나 흘린 물질을 만지지 마세요."),
        ("물질과 접촉시 즉시 20분 이상", "피부나 눈에 닿으면 흐르는 물로 20분 이상 씻으세요."),
        ("구강대구강법으로 인공호흡을 하지 말고", "입으로 직접 인공호흡하지 말고 구조장비를 사용하세요."),
        ("타는 동안 열분해 또는 연소에 의해", "불이 나면 자극적이거나 유독한 연기가 날 수 있습니다."),
        ("이 물질과 관련된 소화시 알콜 포말", "불을 끌 때는 알코올포말, 이산화탄소, 물분무를 사용할 수 있습니다."),
        ("질식소화시 건조한 모래 또는 흙", "작은 불은 마른 모래나 흙으로 덮어 끌 수 있습니다."),
    )
    for pattern, replacement in easy_patterns:
        if pattern in line:
            return replacement

    line = line.replace("의학적인 조치/조언", "진료나 상담")
    line = line.replace("의학적인 조치·조언", "진료나 상담")
    line = line.replace("보호장갑/보호의/보안경/안면보호구", "보호장갑, 보호복, 보안경, 얼굴 보호구")
    line = line.replace("물/…(으)로", "물로")
    line = line.replace("…을(를)", "노출된 부위를")
    line = line.replace("…처치를", "필요한 처치를")
    line = re.sub(r"\(알려진 특정한 영향을.*", "", line).strip()
    line = re.sub(r"\s*:\s*", ": ", line)
    return line


def _is_low_value_msds_line(line):
    low_value_patterns = (
        "사용 전 취급 설명서를 확보",
        "모든 안전 예방조치 문구를 읽고",
        "노출되는 기체/액체의 물리화학적 특성",
        "공기수준을 노출기준 이하",
        "의료인력이 해당물질에 대해 인지",
    )
    return any(pattern in line for pattern in low_value_patterns)


def _xml_items(xml_text):
    root = ElementTree.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        row = {}
        for child in list(item):
            row[child.tag] = child.text or ""
        items.append(row)
    return items


def _api_error(message, status=502):
    return JsonResponse({"results": [], "error": message}, status=status)


def _safe_api_error(label, exc):
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    if status_code:
        return f"{label} API 호출 실패: HTTP {status_code}"
    return f"{label} API 호출 실패"


def _request_float(request, key):
    try:
        return float(request.GET.get(key, ""))
    except (TypeError, ValueError):
        return None


def _pick_float(item, keys):
    for key in keys:
        value = _to_float(item.get(key))
        if value is not None:
            return value
    return None


def _distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(radius * 2 * atan2(sqrt(a), sqrt(1 - a)), 1)


def _sort_nearest(results, lat, lon, limit=3):
    if lat is None or lon is None:
        return results[:limit]
    with_distance = []
    without_distance = []
    for item in results:
        distance = _distance_km(lat, lon, item.get("lat"), item.get("lon"))
        item["distance_km"] = distance
        if distance is None:
            without_distance.append(item)
        else:
            with_distance.append(item)
    with_distance.sort(key=lambda item: item["distance_km"])
    sorted_results = with_distance + without_distance
    return sorted_results if limit is None else sorted_results[:limit]


def _dedupe_places(results):
    seen = set()
    unique = []
    for item in results:
        address_head = (item.get("address") or "").split(",", 1)[0].strip()
        key = (item.get("name") or "", address_head)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _public_data_key(service):
    key = {
        "kma": settings.KMA_API_KEY,
        "nemc": settings.NEMC_API_KEY,
    }.get(service, settings.PUBLIC_DATA_API_KEY)
    return key or ""


def weather_json(request):
    """기상청 초단기예보 기반 작업 주의 정보."""
    api_key = _public_data_key("kma")
    if not api_key:
        return _api_error("KMA_API_KEY 또는 PUBLIC_DATA_API_KEY가 필요합니다.", 503)

    nx = request.GET.get("nx", "60")
    ny = request.GET.get("ny", "127")
    now = timezone.localtime()
    base = now.replace(minute=0, second=0, microsecond=0)
    if now.minute < 45:
        base -= timezone.timedelta(hours=1)

    params = {
        "serviceKey": api_key,
        "pageNo": "1",
        "numOfRows": "100",
        "dataType": "JSON",
        "base_date": base.strftime("%Y%m%d"),
        "base_time": base.strftime("%H%M"),
        "nx": nx,
        "ny": ny,
    }
    cache_key = f"weather:{params['base_date']}:{params['base_time']}:{nx}:{ny}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        res = requests.get(
            "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst",
            params=params,
            timeout=8,
        )
        res.raise_for_status()
        data = res.json()
        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") not in (None, "00"):
            return _api_error(header.get("resultMsg", "기상청 API 응답 오류"))

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        by_time = {}
        for item in items:
            fcst_time = item.get("fcstTime")
            by_time.setdefault(fcst_time, {})[item.get("category")] = item.get("fcstValue")

        hours = []
        for fcst_time, values in sorted(by_time.items())[:6]:
            temp = _to_float(values.get("T1H"))
            wind = _to_float(values.get("WSD"))
            pty = values.get("PTY", "0")
            rain = values.get("RN1", "0")
            warnings = []
            if temp is not None and temp >= 33:
                warnings.append("폭염: 물·그늘·휴식 원칙을 지켜주세요.")
            if temp is not None and temp <= -10:
                warnings.append("한파: 방한장비와 미끄럼 사고를 확인하세요.")
            if pty not in ("0", "", None) or (rain and rain != "강수없음" and rain != "0"):
                warnings.append("강수: 전기작업과 고소작업을 주의하세요.")
            if wind is not None and wind >= 9:
                warnings.append("강풍: 크레인·비계·자재 결속을 확인하세요.")
            hours.append({
                "time": f"{fcst_time[:2]}:{fcst_time[2:]}",
                "temp": temp,
                "rain": rain,
                "wind": wind,
                "warnings": warnings,
            })

        payload = {
            "base_time": f"{params['base_date']} {params['base_time']}",
            "location": {"nx": nx, "ny": ny},
            "hours": hours,
            "is_live_api": True,
        }
        cache.set(cache_key, payload, 20 * 60)
        return JsonResponse(payload)
    except Exception as exc:
        return _api_error(_safe_api_error("기상청", exc))


def _to_float(value):
    try:
        if value in (None, "", "강수없음"):
            return None
        return float(str(value).replace("m/s", ""))
    except (TypeError, ValueError):
        return None


def emergency_rooms_json(request):
    """국립중앙의료원 응급실 실시간 가용병상 정보."""
    api_key = _public_data_key("nemc")
    if not api_key:
        return _api_error("NEMC_API_KEY 또는 PUBLIC_DATA_API_KEY가 필요합니다.", 503)

    stage1 = request.GET.get("stage1", "서울특별시")
    stage2 = request.GET.get("stage2", "강남구")
    lat = _request_float(request, "lat")
    lon = _request_float(request, "lon")
    lat_key = round(lat, 3) if lat is not None else None
    lon_key = round(lon, 3) if lon is not None else None
    cache_key = f"er:{stage1}:{stage2}:{lat_key}:{lon_key}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        if lat is not None and lon is not None:
            results = _fetch_nearby_emergency_rooms(api_key, lat, lon)
        else:
            results = _fetch_regional_emergency_rooms(api_key, stage1, stage2, lat, lon)
        payload = {"results": results, "stage1": stage1, "stage2": stage2, "is_live_api": True}
        cache.set(cache_key, payload, 30 * 60)
        return JsonResponse(payload)
    except Exception as exc:
        return _api_error(_safe_api_error("응급실", exc))


def _fetch_nearby_emergency_rooms(api_key, lat, lon):
    res = requests.get(
        "https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytLcinfoInqire",
        params={
            "serviceKey": api_key,
            "WGS84_LON": str(lon),
            "WGS84_LAT": str(lat),
            "pageNo": "1",
            "numOfRows": "3",
        },
        timeout=4,
    )
    res.raise_for_status()
    items = _xml_items(res.text)
    results = []
    for item in items[:3]:
        item_lat = _pick_float(item, ("latitude", "wgs84Lat", "WGS84_LAT"))
        item_lon = _pick_float(item, ("longitude", "wgs84Lon", "WGS84_LON"))
        distance = _to_float(item.get("distance"))
        results.append({
            "name": item.get("dutyName") or "응급의료기관",
            "address": item.get("dutyAddr") or "",
            "phone": item.get("dutyTel1") or "",
            "bed": "",
            "updated_at": "",
            "lat": item_lat,
            "lon": item_lon,
            "distance_km": round(distance, 1) if distance is not None else _distance_km(lat, lon, item_lat, item_lon),
        })
    results.sort(key=lambda item: item["distance_km"] if item["distance_km"] is not None else 99999)
    return results[:3]


def _fetch_regional_emergency_rooms(api_key, stage1, stage2, lat, lon):
    res = requests.get(
        "https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEmrrmRltmUsefulSckbdInfoInqire",
        params={
            "serviceKey": api_key,
            "STAGE1": stage1,
            "STAGE2": stage2,
            "pageNo": "1",
            "numOfRows": "30",
        },
        timeout=8,
    )
    res.raise_for_status()
    items = _xml_items(res.text)
    results = []
    for item in items:
        detail = _fetch_emergency_room_detail(api_key, item.get("hpid") or item.get("phpid"))
        item_lat = _pick_float(item, ("wgs84Lat", "WGS84_LAT", "latitude", "lat"))
        item_lon = _pick_float(item, ("wgs84Lon", "WGS84_LON", "longitude", "lon"))
        if detail:
            item_lat = item_lat if item_lat is not None else _pick_float(detail, ("wgs84Lat", "WGS84_LAT"))
            item_lon = item_lon if item_lon is not None else _pick_float(detail, ("wgs84Lon", "WGS84_LON"))
        results.append({
            "name": detail.get("dutyName") if detail else item.get("dutyName") or item.get("dutyNm") or item.get("hpid") or "응급의료기관",
            "address": detail.get("dutyAddr") if detail else item.get("dutyAddr") or "",
            "phone": item.get("dutyTel3") or (detail.get("dutyTel3") if detail else "") or (detail.get("dutyTel1") if detail else "") or item.get("dutyTel1") or "",
            "bed": item.get("hvec") or item.get("hvs01") or "",
            "updated_at": item.get("hvidate") or "",
            "lat": item_lat,
            "lon": item_lon,
        })
    return _sort_nearest(results, lat, lon)


def _fetch_emergency_room_detail(api_key, hpid):
    if not hpid:
        return {}
    cache_key = f"er-detail:{hpid}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        res = requests.get(
            "https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytBassInfoInqire",
            params={
                "serviceKey": api_key,
                "HPID": hpid,
                "pageNo": "1",
                "numOfRows": "1",
            },
            timeout=5,
        )
        res.raise_for_status()
        items = _xml_items(res.text)
        detail = items[0] if items else {}
        cache.set(cache_key, detail, 60 * 60 * 24)
        return detail
    except Exception:
        cache.set(cache_key, {}, 60 * 10)
        return {}


def aeds_json(request):
    """국립중앙의료원 AED 위치 정보."""
    api_key = _public_data_key("nemc")
    if not api_key:
        return _api_error("NEMC_API_KEY 또는 PUBLIC_DATA_API_KEY가 필요합니다.", 503)

    stage1 = request.GET.get("stage1", "서울특별시")
    stage2 = request.GET.get("stage2", "강남구")
    lat = _request_float(request, "lat")
    lon = _request_float(request, "lon")
    cache_key = f"aed:{stage1}:{stage2}:{lat}:{lon}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        params = {
            "serviceKey": api_key,
            "Q0": stage1,
            "pageNo": "1",
            "numOfRows": "500" if lat is not None and lon is not None else "30",
        }
        if stage2 and (lat is None or lon is None):
            params["Q1"] = stage2
        res = requests.get(
            "https://apis.data.go.kr/B552657/AEDInfoInqireService/getEgytAedManageInfoInqire",
            params=params,
            timeout=8,
        )
        res.raise_for_status()
        items = _xml_items(res.text)
        results = []
        for item in items:
            org = item.get("org") or item.get("buildPlace") or "AED 설치 장소"
            address = item.get("buildAddress") or item.get("mfgPlace") or ""
            item_lat = _pick_float(item, ("wgs84Lat", "WGS84_LAT", "latitude", "lat"))
            item_lon = _pick_float(item, ("wgs84Lon", "WGS84_LON", "longitude", "lon"))
            results.append({
                "name": org,
                "place": item.get("buildPlace") or "",
                "address": address,
                "manager": item.get("manager") or "",
                "phone": item.get("managerTel") or "",
                "lat": item_lat,
                "lon": item_lon,
            })
        results = _dedupe_places(_sort_nearest(results, lat, lon, limit=None))[:3]
        payload = {"results": results, "stage1": stage1, "stage2": stage2, "is_live_api": True}
        cache.set(cache_key, payload, 30 * 60)
        return JsonResponse(payload)
    except Exception as exc:
        return _api_error(_safe_api_error("AED", exc))

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
