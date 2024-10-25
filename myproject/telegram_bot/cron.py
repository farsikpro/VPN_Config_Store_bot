import logging
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from telegram import Bot
from .models import Client
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

def notify_expiring_subscriptions():
    logger.info("Executing notify_expiring_subscriptions job")
    bot_token = settings.TOKEN
    bot = Bot(token=bot_token)

    now = timezone.now()
    three_days_later = now + timezone.timedelta(days=3)
    logger.info(f"Current time: {now}")
    logger.info(f"Three days later: {three_days_later}")

    # Логируем всех клиентов
    all_clients = Client.objects.all()
    for client in all_clients:
        logger.info(f"Client {client.telegram_id}, subscription_end: {client.subscription_end}, notified: {client.notified}")

    clients = Client.objects.filter(
        subscription_end__lte=three_days_later,
        subscription_end__gte=now,
        notified=False
    )
    logger.info(f"Found {clients.count()} clients with expiring subscriptions")

    for client in clients:
        logger.info(f"Processing client {client.telegram_id}, subscription_end: {client.subscription_end}, notified: {client.notified}")
        remaining_time = client.subscription_end - now
        days = remaining_time.days
        hours = (remaining_time.seconds // 3600) % 24
        minutes = (remaining_time.seconds % 3600) // 60

        message = (
            '⚠️ *Срок действия вашей подписки истекает* ⚠️\n'
            f'Осталось: *{days}* дн. *{hours}* ч. *{minutes}* мин.\n'
            'Пожалуйста, продлите подписку, чтобы продолжить пользоваться услугами.'
        )

        try:
            async_to_sync(bot.send_message)(
                chat_id=client.telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Notification sent to client {client.telegram_id}")

            # Обновляем поле notified после успешной отправки
            client.notified = True
            client.save()
            logger.info(f"Client {client.telegram_id} notified status set to True")
        except Exception as e:
            logger.exception(f"Error sending notification to client {client.telegram_id}: {e}")