from django.urls import path
from . import views

app_name = 'health'

urlpatterns = [
    path('map/', views.ClinicMapView.as_view(), name='map'),
    path('api/clinics/', views.clinics_json, name='api_clinics'),
    path('api/alerts/', views.safety_alerts_json, name='api_alerts'),
]
