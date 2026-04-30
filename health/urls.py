from django.urls import path
from . import views

app_name = 'health'

urlpatterns = [
    path('map/', views.ClinicMapView.as_view(), name='map'),
    path('weather/', views.WeatherNoticeView.as_view(), name='weather'),
    path('emergency/', views.EmergencyHelpView.as_view(), name='emergency'),
    path('api/clinics/', views.clinics_json, name='api_clinics'),
    path('api/alerts/', views.safety_alerts_json, name='api_alerts'),
    path('api/weather/', views.weather_json, name='api_weather'),
    path('api/emergency-rooms/', views.emergency_rooms_json, name='api_emergency_rooms'),
    path('api/aeds/', views.aeds_json, name='api_aeds'),
]
