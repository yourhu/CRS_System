from django.urls import path
from . import views

'''urlpatterns = [
    path('chat/', views.ChatView.as_view(), name='chat'),
]'''
from django.urls import path
from django.urls import path
#from .views import ChatView, ConversationHistoryView, ChatPageView


#app_name = 'chat'

'''urlpatterns = [
    path('chat/', ChatPageView.as_view(), name='chat_page'),  # 渲染页面
    path('chat/api/', ChatView.as_view(), name='chat_api'),   # API 端点
    path('chat/history/', views.ConversationHistoryView.as_view(), name='chat_history'),
]
'''
from django.urls import path
from .views import ChatView, ConversationHistoryView

app_name = 'chat'

urlpatterns = [
    path('api/', ChatView.as_view(), name='chat_api'),
    path('history/', ConversationHistoryView.as_view(), name='chat_history'),
]