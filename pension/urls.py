from django.urls import path
from . import views

app_name = 'pension'

urlpatterns = [
    path('search/', views.PensionSearchView.as_view(), name='search'),
    path('api/search/', views.search_sites_json, name='api_search'),
]
