from django.db import models


class PublicDataSyncState(models.Model):
    key = models.CharField(max_length=80, unique=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, blank=True)
    last_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.key}: {self.last_status}"
