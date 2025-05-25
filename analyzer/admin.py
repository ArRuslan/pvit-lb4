from django.contrib import admin

from .models import WebsiteScan, Violation


class ViolationInline(admin.TabularInline):
    model = Violation
    extra = 0


@admin.register(WebsiteScan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('url', 'timestamp')
    inlines = [ViolationInline]
