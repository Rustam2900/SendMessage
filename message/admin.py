from django.contrib import admin
from message.models import BotAdmin, Channel, Post


@admin.register(BotAdmin)
class BotAdminAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'full_name', 'tg_username')
    search_fields = ('id', 'username', 'tg_username', 'telegram_id')


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'channel_id', 'active')
    search_fields = ('id', 'name', 'channel_id')
    list_filter = ('active',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'sent_count', 'created_at')
    search_fields = ('title', 'message')
    list_filter = ('created_at',)
