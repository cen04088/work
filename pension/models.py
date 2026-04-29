from django.db import models

class PensionSite(models.Model):
    project_name = models.CharField(max_length=300)
    company_name = models.CharField(max_length=200)
    total_amount = models.CharField(max_length=50, blank=True)
    client_org = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=300, blank=True)

