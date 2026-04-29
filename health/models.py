from django.db import models

class HealthClinic(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    region = models.CharField(max_length=50)
    phone = models.CharField(max_length=50, blank=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)

