from django.contrib import admin
from .models import Document, AnalysisRequest, Report, Suggestion


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


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "user", "priority", "status", "created_at"]
    list_filter = ["category", "priority", "status", "created_at"]
    search_fields = ["title", "description", "user__username"]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_editable = ["priority", "status"]
    fieldsets = (
        ("Sugestão", {
            "fields": ("id", "user", "category", "title", "description"),
        }),
        ("Gestão Interna", {
            "fields": ("priority", "status", "admin_notes"),
            "description": "Campos visíveis apenas para administradores.",
        }),
        ("Datas", {
            "fields": ("created_at", "updated_at"),
        }),
    )
