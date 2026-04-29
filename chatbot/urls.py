from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('api/', views.chat_api, name='api_chat'),
]
