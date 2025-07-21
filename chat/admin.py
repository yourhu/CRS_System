from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Conversation, Message, Recommendation

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'current_state', 'created_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'message_type', 'created_at')

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'algorithm', 'created_at')