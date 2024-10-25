from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from .cron import notify_expiring_subscriptions
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def start():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Планируем задачу с увеличенным misfire_grace_time
    scheduler.add_job(
        notify_expiring_subscriptions,
        trigger='interval',
        days=1,
        name='notify_expiring_subscriptions',
        jobstore='default',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
    )

    scheduler.start()
    logger.info("Scheduler started!")