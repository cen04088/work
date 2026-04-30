import csv
from datetime import date
from pathlib import Path
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.conf import settings

class JobListView(TemplateView):
    template_name = 'jobs/list.html'

def get_jobs_json(request):
    """건설근로자공제회 취업정보 DB 연동"""
    region = request.GET.get("region", "")
    
    from .models import JobPosting
    from django.db.models import Q
    qs = JobPosting.objects.all()
    if region:
        if region == "경기" or region == "경기 (수원 등)":
            qs = qs.filter(Q(work_region__icontains="경기") | Q(work_region__icontains="수원"))
        else:
            qs = qs.filter(work_region__icontains=region)
        
    jobs = []
    for c in qs[:20]: # 최대 20개만
        jobs.append({
            "company": c.company_name,
            "title": c.job_title,
            "region": c.work_region,
            "wage": c.wage,
            "phone": c.contact_phone,
            "url": c.detail_url,
        })
    return JsonResponse({"jobs": jobs})

def get_centers_json(request):
    """건설근로자공제회 무료 취업지원센터 데이터 반환"""
    region = request.GET.get("region", "")
    
    from .models import EmploymentSupportCenter
    from django.db.models import Q
    
    qs = EmploymentSupportCenter.objects.all()
    if region:
        # 권역 필터링
        qs = qs.filter(Q(region__icontains=region) | Q(location__icontains=region))
        
    centers = []
    for c in qs:
        centers.append({
            "region": c.region,
            "name": c.name,
            "location": c.location,
            "phone": c.phone_number,
        })
    return JsonResponse({"centers": centers})


def get_training_json(request):
    """건설근로자공제회 건설기능인력 훈련기관 CSV 기반 조회."""
    region = request.GET.get("region", "").strip()
    today = date.today().isoformat()
    csv_path = Path(settings.BASE_DIR) / "data" / "건설근로자공제회_건설기능인력 훈련기관 정보_20250414.csv"

    trainings = []
    try:
        with csv_path.open("r", encoding="cp949", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                address = row.get("훈련기관 주소", "")
                start_date = row.get("개시일", "")
                if region and region not in address:
                    continue
                if start_date and start_date < today:
                    continue
                trainings.append({
                    "name": row.get("훈련기관명", ""),
                    "course": row.get("훈련직종", ""),
                    "type": row.get("훈련구분", ""),
                    "start": start_date,
                    "end": row.get("종료일", ""),
                    "capacity": row.get("인원", ""),
                    "address": address,
                    "phone": row.get("훈련기관 전화번호", ""),
                })
    except FileNotFoundError:
        return JsonResponse({"trainings": [], "error": "훈련기관 CSV 파일을 찾을 수 없습니다."}, status=404)

    trainings.sort(key=lambda item: item["start"] or "9999-99-99")
    return JsonResponse({"trainings": trainings[:10]})
