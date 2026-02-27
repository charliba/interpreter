from django.contrib import admin
from .models import Document, AnalysisRequest, Report


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "file_type", "file_size_display", "uploaded_by", "uploaded_at"]
    list_filter = ["file_type", "uploaded_at"]
    search_fields = ["original_filename"]
    readonly_fields = ["uploaded_at"]


@admin.register(AnalysisRequest)
class AnalysisRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id", "document", "professional_area", "report_type",
        "language", "status", "requested_by", "created_at"
    ]
    list_filter = ["status", "professional_area", "report_type", "language"]
    search_fields = ["user_objective", "document__original_filename"]
    readonly_fields = ["created_at", "completed_at"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "analysis", "generated_at"]
    readonly_fields = ["generated_at"]
