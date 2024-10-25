from django.core.management.base import BaseCommand
from telegram_bot.scheduler import start
import time

class Command(BaseCommand):
    help = 'Запуск планировщика задач'

    def handle(self, *args, **options):
        start()
        self.stdout.write(self.style.SUCCESS('Scheduler started'))

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Scheduler stopped'))