from django.urls import path
from .views import InitiateLead, MessageList, ReplyView

app_name = 'messaging'

urlpatterns = [
    path('', MessageList.as_view(), name='list'),
    path('create-lead/', InitiateLead.as_view(), name='create'),
    path('reply/<uuid:pk>/', ReplyView.as_view(), name='reply'),
]