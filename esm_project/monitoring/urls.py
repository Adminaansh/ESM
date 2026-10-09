# monitoring/urls.py
from django.urls import path
from .views import (
    LiveExecutionControlView,
    InitiateExecutionAPI,
    LiveExecutionListView,
    LiveExecutionHistoryView,
    HistoryExecutionOutputAPI,
    IngestTelemetryLogsAPI,
    GlobalLiveConsoleAPI,
    DeleteExecutionAPI,
    ExternalAPIStatusCallbackAPI,
    IngestView, 
    BatchView,
    LogErrorsView, 
    StatsView
)

urlpatterns = [
    # Control Hub (GET: filter matrix / POST: actions)
    path('execution/control/', LiveExecutionControlView.as_view(), name='execution-control'),
    
    # Telemetry and Execution Hooks
    path('execution/start/', InitiateExecutionAPI.as_view(), name='execution-start'),
    path('execution/list/', LiveExecutionListView.as_view(), name='execution-list'),
    path('execution/history/', LiveExecutionHistoryView.as_view(), name='execution-history'),
    path('execution/history/<int:process_no>/output/', HistoryExecutionOutputAPI.as_view(), name='history-output'),
    path('execution/log/', IngestTelemetryLogsAPI.as_view(), name='execution-log'),
    path('execution/external/callback/', ExternalAPIStatusCallbackAPI.as_view(), name='external-api-callback'),
    path('process/<int:process_no>/stream/', GlobalLiveConsoleAPI.as_view(), name='global-console-stream'),
    # Force delete/archive a live execution
    path('execution/<uuid:execution_id>/delete/', DeleteExecutionAPI.as_view(), name='execution-delete'),



    path("ingest/", IngestView.as_view()),
    path("batch/", BatchView.as_view()),
    path("stats/", StatsView.as_view()),

   path("log-errors/", LogErrorsView.as_view()),
]