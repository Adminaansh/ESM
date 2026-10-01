from django.urls import path
from . import views

urlpatterns = [
    # Lifecycle
    path('run', views.RunJobView.as_view()),
    path('kill/<uuid:id>', views.KillJobView.as_view()),
    path('pause', views.PauseJobView.as_view()),
    path('resume', views.ResumeJobView.as_view()),
    path('force-ok', views.ForceOKView.as_view()),
    
    # Bulk
    path('bulk/kill', views.BulkKillView.as_view()),
    path('bulk/pause', views.BulkPauseView.as_view()),
    
    # Config/Meta
    path('config/<uuid:id>/priority', views.SetPriorityView.as_view()),
    path('meta/<uuid:id>/topology', views.GetTopologyView.as_view()),
    
    # Placeholder for remaining 11 APIs (e.g., /unlock, /lock, /set-ttl, etc.)
    # path('lock/<uuid:id>', ...),
]