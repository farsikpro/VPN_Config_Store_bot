from django.db import models

class Client(models.Model):
    telegram_id = models.CharField(max_length=50, unique=True)
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    assigned_config = models.ForeignKey('VPNConfig', null=True, blank=True, on_delete=models.SET_NULL)
    notified = models.BooleanField(default=False)

    def __str__(self):
        return f"Client {self.telegram_id}"

    def __str__(self):
        return f"Client {self.telegram_id}"

class VPNConfig(models.Model):
    name = models.CharField(max_length=100)
    config_text = models.TextField()
    is_assigned = models.BooleanField(default=False)

    def __str__(self):
        return self.name
