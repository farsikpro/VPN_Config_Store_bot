import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    try:
        from django.core.management import execute_from_command_line
        from django.core.wsgi import get_wsgi_application

        # Инициализация приложения
        application = get_wsgi_application()

        # # Запуск планировщика
        # from telegram_bot.scheduler import start
        # start()

    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django..."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()