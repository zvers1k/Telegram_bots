import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from bot_back_settings import Sayany_bot_token

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = Sayany_bot_token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"👋 Привет!\n"
        f"🆔 Твой ID: {user.id}\n"
        f"💬 ID этого чата: {chat.id}\n\n"
        f"📢 Чтобы получить ID канала:\n"
        f"1. Добавь меня в канал как администратора\n"
        f"2. Перешли мне любое сообщение ИЗ КАНАЛА\n"
        f"3. Я покажу ID канала"
    )

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пересланных сообщений"""
    try:
        message = update.message
        
        # Проверяем, что сообщение переслано и есть информация о чате
        if message.forward_origin:
            if hasattr(message.forward_origin, 'chat'):
                channel = message.forward_origin.chat
                
                if channel.type == "channel":
                    await message.reply_text(
                        f"📢 Информация о канале:\n"
                        f"Название: {channel.title}\n"
                        f"ID: {channel.id}\n"
                        f"Username: @{channel.username if channel.username else 'нет'}\n\n"
                        f"🔧 ID для API: {channel.id}\n"
                        f"💡 Формат: {channel.id}"
                    )
                    return
                    
        # Если сообщение переслано не из канала
        await message.reply_text(
            "❌ Это сообщение не из канала!\n\n"
            "📝 Чтобы получить ID канала:\n"
            "1. Добавь меня в канал как администратора\n"
            "2. Перешли сообщение ИМЕННО ИЗ КАНАЛА\n"
            "3. Не из группы, а именно из канала!"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def channel_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о получении ID канала"""
    await update.message.reply_text(
        "📢 Как получить ID канала:\n\n"
        "1. ✅ Добавьте бота в канал как администратора\n"
        "2. ✅ Дайте права на 'Отправка сообщений'\n"
        "3. 📨 Перешлите любое сообщение ИЗ КАНАЛА боту\n"
        "4. 🎉 Бот покажет ID канала\n\n"
        "❗ Важно: сообщение должно быть переслано именно из канала, а не из группы!"
    )

async def get_my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Попытка получить список каналов через API"""
    try:
        # Этот метод может не работать для обычных ботов
        await update.message.reply_text(
            "📋 Список каналов можно получить только через пересланные сообщения\n\n"
            "Просто перешлите любое сообщение из канала, и я покажу его ID"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("channel", channel_info))
    app.add_handler(CommandHandler("mychannels", get_my_channels))
    
    # Обработчик пересланных сообщений
    app.add_handler(MessageHandler(filters.FORWARDED, handle_forwarded_message))
    
    print("🤖 Бот запущен!")
    print("📢 Для получения ID канала перешлите сообщение из канала боту")
    app.run_polling()

if __name__ == "__main__":
    main()