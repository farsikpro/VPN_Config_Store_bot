from django.core.management.base import BaseCommand
from telegram_bot.bot import main

class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **options):
        main()