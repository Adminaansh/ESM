"""
URL configuration for esm_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.generic import TemplateView

urlpatterns = [

    # Main Operator GUI Interface Portal
    path('', TemplateView.as_view(template_name='dashboard.html'), name='operator-gui'),


    path('admin/', admin.site.urls),
    
    # IAM Module - Login Endpoints
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Include other module URLs as we build them
    # path('api/v1/jobs/', include('apps.studio.urls')),

    # IAM Module APIs (Protected)
    path('api/v1/iam/',include('iam.urls')),
    path('api/v1/studio/',include('studio.urls')),
    path('api/v1/engine/', include('engine.urls')),
    path('api/infrastructure/', include('infrastructure.urls')),
    path('api/monitoring/', include('monitoring.urls')),
    path('api/scheduler/', include('scheduler.urls')),
    path('api/vault/', include('vault.urls')),
    path('api/compliance/', include('compliance.urls')),
    path('api/maintenance/', include('maintenance.urls')),
    path('exec/', include('execution_hub.urls')),
]



