from django.db import models
from django.conf import settings

class Conversation(models.Model):
    class State(models.TextChoices):
        INIT = 'init', 'Init'
        COLLECTING = 'collecting', 'Collecting'
        RECOMMENDING = 'recommending', 'Recommending'
        FEEDBACK = 'feedback', 'Feedback'
        CLOSED = 'closed', 'Closed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    current_state = models.CharField(max_length=20, choices=State.choices, default=State.INIT)
    context = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.id} ({self.user})"

class Message(models.Model):
    class MessageType(models.TextChoices):
        USER_TEXT = 'user', 'User'
        SYSTEM_TEXT = 'system', 'System'
        PRODUCT_CARD = 'product', 'Product'

    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    message_type = models.CharField(max_length=20, choices=MessageType.choices)
    content = models.TextField()
    structured_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.id} ({self.message_type})"

class Recommendation(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='recommendations', on_delete=models.CASCADE)
    algorithm = models.CharField(max_length=50)
    products = models.ManyToManyField('products.Product')
    feedback = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation {self.id} ({self.algorithm})"