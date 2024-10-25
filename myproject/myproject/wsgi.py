import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = get_wsgi_application()

# Удалите или закомментируйте следующую строку
# from telegram_bot.scheduler import start
# start()