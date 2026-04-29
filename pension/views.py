import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

class PensionSearchView(TemplateView):
    template_name = 'pension/search.html'

def search_sites_json(request):
    """현장명/시공사 검색 (DB 연동)"""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    
    from .models import PensionSite
    from django.db.models import Q
    sites = PensionSite.objects.filter(
        Q(project_name__icontains=q) |
        Q(company_name__icontains=q)
    )[:20]
            
    results = [
        {
            "id": site.id,
            "project": site.project_name,
            "company": site.company_name,
            "period": site.address, # 공사기간 대신 주소 사용
            "enrolled": True,
        }
        for site in sites
    ]
    return JsonResponse({"results": results})

