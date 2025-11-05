import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bot_back_settings import Sayany_bot_token

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота (замените на свой)
BOT_TOKEN = Sayany_bot_token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat = update.effective_chat
    
    message = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"🆔 Твой ID пользователя: {user.id}\n"
        f"💬 ID этого чата: {chat.id}\n\n"
        f"📝 Имя пользователя: @{user.username if user.username else 'не установлен'}\n"
        f"👤 Полное имя: {user.full_name}\n\n"
        "📋 Просто отправь любое сообщение, и я покажу ID чата!\n\n"
        "📝 Команды:\n"
        "/start - начать работу\n"
        "/help - справка\n"
        "/myid - мой ID\n"
        "/chatid - ID чата"
    )
    
    await update.message.reply_text(message)

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик любого сообщения"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        message = (
            f"💬 Это приватный чат\n"
            f"🆔 Твой ID пользователя: {user.id}\n"
            f"💬 ID чата: {chat.id}"
        )
    elif chat.type in ["group", "supergroup"]:
        message = (
            f"👥 Это групповой чат: {chat.title}\n"
            f"💬 ID группы: {chat.id}\n"
            f"👤 Твой ID пользователя: {user.id}"
        )
    elif chat.type == "channel":
        message = (
            f"📢 Это канал: {chat.title}\n"
            f"💬 ID канала: {chat.id}"
        )
    else:
        message = f"💬 ID чата: {chat.id}"
    
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🤖 Бот для получения ID чатов и пользователей\n\n"
        "📋 Команды:\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту справку\n"
        "/myid - показать ваш ID пользователя\n"
        "/chatid - показать ID текущего чата\n\n"
        "💡 Просто отправьте любое сообщение, и бот ответит с ID чата!"
    )
    await update.message.reply_text(help_text)

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /myid"""
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 Ваш ID пользователя: {user.id}\n"
        f"📝 Username: @{user.username if user.username else 'не установлен'}"
    )

async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /chatid"""
    chat = update.effective_chat
    
    if chat.type == "private":
        chat_type = "приватный чат"
    elif chat.type in ["group", "supergroup"]:
        chat_type = f"групповой чат: {chat.title}"
    elif chat.type == "channel":
        chat_type = f"канал: {chat.title}"
    else:
        chat_type = "чат"
    
    await update.message.reply_text(f"💬 ID {chat_type}: {chat.id}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main():
    """Основная функция"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("chatid", chatid_command))
    
    # Обработчик для любых текстовых сообщений
    application.add_handler(MessageHandler(filters.COMMAND, get_chat_id))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()