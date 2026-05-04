from django.db import models

class HealthClinic(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    region = models.CharField(max_length=50)
    phone = models.CharField(max_length=50, blank=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)


class SafetyExcellentWorkplace(models.Model):
    post_number = models.CharField(max_length=30, blank=True)
    labor_office = models.CharField(max_length=80, blank=True)
    workplace_name = models.CharField(max_length=200)
    construction_site_name = models.CharField(max_length=200, blank=True)
    recognized_date = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["-recognized_date", "workplace_name"]
        indexes = [
            models.Index(fields=["workplace_name"]),
            models.Index(fields=["construction_site_name"]),
            models.Index(fields=["labor_office"]),
        ]

    def __str__(self):
        return self.workplace_name

