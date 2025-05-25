from django.contrib.auth.models import User
from django.db import models

class WebsiteScan(models.Model):
    url = models.URLField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.url} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class Violation(models.Model):
    scan = models.ForeignKey(WebsiteScan, on_delete=models.CASCADE, related_name='violations')
    violation_id = models.CharField(max_length=200)
    impact = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    help_text = models.TextField()
    help_url = models.URLField()
    failure_summary = models.TextField()
    html_snippet = models.TextField()

    def __str__(self):
        return self.violation_id
