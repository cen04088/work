import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

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

