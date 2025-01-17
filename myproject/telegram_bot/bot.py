import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from django.conf import settings
from django.utils import timezone
from .models import Client, VPNConfig
from asgiref.sync import sync_to_async
import qrcode
from io import BytesIO
import html
import os

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = ''
OWNER_TELEGRAM_ID = ''

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Купить товар'], ['Статус'], ['Задать вопрос'], ['Инструкция']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Добро пожаловать! Выберите опцию:', reply_markup=reply_markup)

async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        'Стоимость подписки:\n'
        '1 месяц = 100р\n\n'
        'Реквизиты:\n'
        'Сбер — 2202 2050 7610 7470\n\n'
        'После оплаты, пожалуйста, отправьте в ответном сообщении скриншот об оплате.'
    )
    await update.message.reply_text(message)

async def receive_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        await context.bot.send_message(
            chat_id=OWNER_TELEGRAM_ID,
            text=f"Новый платеж от {update.message.from_user.id}"
        )
        await context.bot.forward_message(
            chat_id=OWNER_TELEGRAM_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        await update.message.reply_text('Спасибо! Ваш платеж на проверке.')
    else:
        await update.message.reply_text('Пожалуйста, отправьте изображение.')

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Проверка статуса для пользователя {update.message.from_user.id}")
    try:
        # Получаем клиента асинхронно
        client = await sync_to_async(Client.objects.get)(telegram_id=str(update.message.from_user.id))
        now = timezone.now()
        if client.subscription_end and client.subscription_end > now:
            remaining_time = client.subscription_end - now
            days = remaining_time.days
            hours = remaining_time.seconds // 3600
            minutes = (remaining_time.seconds % 3600) // 60

            # Обернуть доступ к assigned_config
            assigned_config = await sync_to_async(lambda: client.assigned_config)()

            if assigned_config:
                config_name = assigned_config.name
            else:
                config_name = 'Не назначен'

            await update.message.reply_text(
                f'Ваша подписка активна.\n'
                f'Осталось: {days} дн. {hours} ч. {minutes} мин.\n'
                f'Ваш конфиг: {config_name}'
            )
        else:
            await update.message.reply_text('Ваша подписка истекла.')
    except Client.DoesNotExist:
        logger.error(f"Клиент с ID {update.message.from_user.id} не найден в базе данных.")
        await update.message.reply_text('У вас нет активной подписки.')
    except Exception as e:
        logger.exception(f"Ошибка при проверке статуса для пользователя {update.message.from_user.id}: {e}")
        await update.message.reply_text('Произошла ошибка при проверке статуса. Пожалуйста, попробуйте позже.')

async def send_vpn_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получена команда /send_config от пользователя {update.message.from_user.id}")

    if str(update.message.from_user.id) != str(OWNER_TELEGRAM_ID):
        logger.warning("Попытка использования /send_config неавторизованным пользователем.")
        await update.message.reply_text('У вас нет прав для этой команды.')
        return

    args = context.args
    if not args:
        await update.message.reply_text('Использование: /send_config TELEGRAM_ID [ДНИ]')
        return

    telegram_id = args[0]
    logger.info(f"Отправка конфига клиенту {telegram_id}")

    # Определяем количество дней подписки
    if len(args) >= 2:
        try:
            days = int(args[1])
        except ValueError:
            await update.message.reply_text('Пожалуйста, укажите корректное количество дней подписки.')
            return
    else:
        days = 30  # По умолчанию 30 дней

    # Получить или создать клиента
    client, created = await sync_to_async(Client.objects.get_or_create)(telegram_id=telegram_id)

    # Оберните доступ к client.assigned_config
    assigned_config = await sync_to_async(lambda: client.assigned_config)()

    if assigned_config:
        vpn_config = assigned_config
    else:
        # Получить следующий доступный конфиг
        vpn_config = await sync_to_async(get_next_available_config)()
        if not vpn_config:
            await update.message.reply_text('Нет доступных конфигов для назначения.')
            return
        client.assigned_config = vpn_config
        vpn_config.is_assigned = True
        # Сохранение объектов
        await sync_to_async(vpn_config.save)()
        await sync_to_async(client.save)()

    # Отправить конфиг клиенту
    try:
        config_text = vpn_config.config_text

        # Генерация QR-кода
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(config_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Сохранение изображения в буфер
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Экранирование HTML-символов в config_text
        config_text_escaped = html.escape(config_text)

        # Формирование сообщения с использованием тега <pre> для моноширинного шрифта
        message_text = f'<pre>{config_text_escaped}</pre>'

        await context.bot.send_message(
            chat_id=telegram_id,
            text=message_text,
            parse_mode='HTML'
        )

        # Отправка QR-кода
        await context.bot.send_photo(
            chat_id=telegram_id,
            photo=buffer,
            caption='QR-код вашего конфига.'
        )

        logger.info(f"Конфиг {vpn_config.name} отправлен клиенту {telegram_id}")
    except Exception as e:
        logger.exception(f"Ошибка при отправке конфига клиенту {telegram_id}: {e}")
        await update.message.reply_text(f"Не удалось отправить конфиг клиенту {telegram_id}.")
        return

    # Обновить информацию о подписке
    now = timezone.now()
    if client.subscription_end and client.subscription_end > now:
        client.subscription_end += timezone.timedelta(days=days)
    else:
        client.subscription_start = now
        client.subscription_end = now + timezone.timedelta(days=days)

    client.notified = False  # Сбрасываем уведомление
    await sync_to_async(client.save)()
    logger.info(f"Клиент {telegram_id} сохранён в базе данных. Подписка до {client.subscription_end}")

    await update.message.reply_text(
        f'Конфиг отправлен клиенту {telegram_id}.\nПодписка активна до {client.subscription_end.strftime("%d.%m.%Y %H:%M:%S")}.'
    )

def get_next_available_config():
    return VPNConfig.objects.filter(is_assigned=False).first()
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('is_asking_question'):
        question = update.message.text
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name

        # Отправляем вопрос владельцу
        await context.bot.send_message(
            chat_id=OWNER_TELEGRAM_ID,
            text=f"📩 *Вопрос от {user_name} (ID: {user_id}):*\n{question}",
            parse_mode='Markdown'
        )

        await update.message.reply_text('Ваш вопрос отправлен. Ожидайте ответ.')
        # Сбрасываем флаг
        context.user_data['is_asking_question'] = False
    else:
        await update.message.reply_text('Извините, я не понимаю эту команду. Пожалуйста, используйте кнопки для навигации.')

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != str(OWNER_TELEGRAM_ID):
        await update.message.reply_text('У вас нет прав для этой команды.')
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text('Использование: /reply USER_ID Ваш ответ')
        return

    user_id = args[0]
    reply_text = ' '.join(args[1:])

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📨 *Ответ на ваш вопрос:*\n{reply_text}",
            parse_mode='Markdown'
        )
        await update.message.reply_text(f'Ответ отправлен пользователю {user_id}.')
    except Exception as e:
        logger.exception(f"Ошибка при отправке ответа пользователю {user_id}: {e}")
        await update.message.reply_text(f'Не удалось отправить сообщение пользователю {user_id}.')

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Пожалуйста, напишите свой вопрос, и мы ответим вам в ближайшее время.')
    # Устанавливаем флаг, что пользователь сейчас в режиме ввода вопроса
    context.user_data['is_asking_question'] = True

async def send_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Вот инструкции для использования:')
    files = [
        ('VPN для Android (v2box).pdf', 'VPN для Android (v2box).pdf'),
        ('VPN для iPhone (v2box).pdf', 'VPN для iPhone (v2box).pdf'),
        ('VPN для Windows.pdf', 'VPN для Windows.pdf'),
    ]
    for file_name, caption in files:
        file_path = os.path.join(settings.BASE_DIR, 'instructions', file_name)
        try:
            with open(file_path, 'rb') as file:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=file, caption=caption)
        except Exception as e:
            logger.exception(f"Ошибка при отправке файла {file_name}: {e}")
            await update.message.reply_text(f'Не удалось отправить файл {file_name}.')

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('send_config', send_vpn_config))
    application.add_handler(CommandHandler('reply', reply_to_user))

    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.Regex('^Купить товар$'), buy_product))
    application.add_handler(MessageHandler(filters.Regex('^Статус$'), check_status))
    application.add_handler(MessageHandler(filters.Regex('^Задать вопрос$'), ask_question))
    application.add_handler(MessageHandler(filters.Regex('^Инструкция$'), send_instructions))
    application.add_handler(MessageHandler(filters.PHOTO, receive_payment_screenshot))

    # Обработчик для неизвестных сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
