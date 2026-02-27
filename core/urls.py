"""core/urls.py — Rotas principais do interpretador"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_view, name="upload"),
    path("analysis/<int:analysis_id>/", views.analysis_status_view, name="analysis_status"),
    path("analysis/<int:analysis_id>/poll/", views.analysis_poll_view, name="analysis_poll"),
    path("analysis/<int:analysis_id>/retry/", views.retry_view, name="analysis_retry"),
    path("analysis/<int:analysis_id>/edit/", views.edit_analysis_view, name="analysis_edit"),
    path("report/<int:analysis_id>/", views.report_view, name="report"),
    path("report/<int:analysis_id>/download/<str:format>/", views.download_view, name="download"),
    path("history/", views.history_view, name="history"),
]
