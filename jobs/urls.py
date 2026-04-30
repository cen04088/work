from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.JobListView.as_view(), name='list'),
    path('api/jobs/', views.get_jobs_json, name='api_jobs'),
    path('api/centers/', views.get_centers_json, name='api_centers'),
    path('api/training/', views.get_training_json, name='api_training'),
]
