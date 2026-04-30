from django.db import models

class JobPosting(models.Model):
    wnet_id = models.CharField(max_length=50, unique=True)
    company_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=300)
    work_region = models.CharField(max_length=100)
    wage = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=50, blank=True)
    detail_url = models.URLField(blank=True)

class EmploymentSupportCenter(models.Model):
    region = models.CharField(max_length=50, help_text="권역 (예: 서울, 경기/인천 등)")
    name = models.CharField(max_length=100, help_text="센터명")
    location = models.CharField(max_length=200, help_text="상세 지역")
    phone_number = models.CharField(max_length=50, help_text="연락처")
    operator = models.CharField(max_length=100, blank=True, help_text="운영기관")
    operating_hours = models.CharField(max_length=50, blank=True, help_text="운영시간")
    source_updated_at = models.CharField(max_length=20, blank=True, help_text="데이터 수정일")

    def __str__(self):
        return f"[{self.region}] {self.name}"

