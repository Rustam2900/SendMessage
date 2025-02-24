from django.db import models


class BotAdmin(models.Model):
    full_name = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    telegram_id = models.CharField(max_length=255, unique=True)
    tg_username = models.CharField(max_length=255, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admin: {self.username} (ID: {self.telegram_id})"


class Channel(models.Model):
    channel_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Channel: {self.name} ({self.channel_id})"


class Post(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    video_url = models.URLField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    channels_sent = models.ManyToManyField(Channel, null=True, blank=True)
    sent_count = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return f"Post: {self.title}"
