from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User, UserInfo

@receiver(post_save, sender=User)
def create_user_info_model(sender, instance, created, **kwargs):
    if created:
        UserInfo.objects.get_or_create(user=instance)

