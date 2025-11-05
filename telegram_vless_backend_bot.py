import logging
import requests
import json
import uuid
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
from bot_back_settings import Vless_bot_token, XUI_PANEL_URL, XUI_PANEL_URL, XUI_USERNAME, XUI_PASSWORD, SERVER_IP, SERVER_PORT, REALITY_PUBLIC_KEY, REALITY_SHORT_ID, ADMIN_TELEGRAM_ID 


# # Конфигурация
BOT_TOKEN = Vless_bot_token
# XUI_PANEL_URL = "http://146.103.123.46:2053"
# XUI_USERNAME = "admin"
# XUI_PASSWORD = "hjxXc71b9bvR7Bh969~2"

# # Reality настройки
# SERVER_IP = "146.103.123.46"
# SERVER_PORT = "443"
# REALITY_PUBLIC_KEY = "OGFybHtMLkRQPoEEL_c1yQe37sGIs-3VUtWkMmkMYxA"
# REALITY_SHORT_ID = "53f7"

# # Админ
# ADMIN_TELEGRAM_ID = 860602580

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class VPNBot:
    def __init__(self):
        self.session = requests.Session()
        self.user_data_cache = {}  # Временное хранилище данных пользователей
        self.setup_session()
    
    def setup_session(self):
        """Настройка сессии для работы с API"""
        try:
            # Логинимся один раз при старте бота
            login_data = {
                "username": XUI_USERNAME,
                "password": XUI_PASSWORD
            }
            response = self.session.post(f"{XUI_PANEL_URL}/login", data=login_data)
            if response.status_code == 200:
                logging.info("✅ Успешная авторизация в 3X-UI")
            else:
                logging.error(f"❌ Ошибка авторизации: {response.status_code}")
        except Exception as e:
            logging.error(f"❌ Ошибка настройки сессии: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Проверяем есть ли у пользователя активный VPN
        has_vpn = await self.check_user_has_vpn(user.id)
        
        if has_vpn:
            keyboard = [
                [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
                [InlineKeyboardButton("🗑️ Удалить мой VPN", callback_data="delete_vpn")],
                [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("📱 Создать VPN", callback_data="create_vpn")],
                [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
            ]
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я бот для управления VPN сервисом.\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

    async def check_user_has_vpn(self, telegram_id: int) -> bool:
        """Проверяет есть ли у пользователя VPN в 3X-UI"""
        try:
            users = await self.get_all_users_from_xui()
            for user in users:
                if f"tg_{telegram_id}" in user['email']:
                    return True
            return False
        except Exception as e:
            logging.error(f"Ошибка проверки пользователя: {e}")
            return False

    async def get_all_users_from_xui(self):
        """Получает всех пользователей из 3X-UI"""
        try:
            response = self.session.get(f"{XUI_PANEL_URL}/panel/api/inbounds/list")
            if response.status_code != 200:
                return []
            
            data = response.json()
            all_users = []
            
            for inbound in data.get('obj', []):
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                
                for client in clients:
                    all_users.append({
                        'email': client.get('email', ''),
                        'uuid': client.get('id', ''),
                        'flow': client.get('flow', ''),
                        'total_gb': client.get('totalGB', 0),
                        'enable': client.get('enable', True),
                        'inbound': inbound.get('remark', ''),
                        'inbound_id': inbound.get('id')
                    })
            
            return all_users
        except Exception as e:
            logging.error(f"Ошибка получения пользователей: {e}")
            return []

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "create_vpn":
            await self.ask_user_name(query, context)
        elif query.data == "my_stats":
            await self.show_stats_callback(query, context)
        elif query.data == "delete_vpn":
            await self.delete_vpn_user(query, context)
        elif query.data == "confirm_delete":
            await self.confirm_delete_vpn(query, context)
        elif query.data == "cancel_delete":
            await self.cancel_delete(query, context)
        elif query.data == "help":
            await self.show_help_callback(query, context)

    async def ask_user_name(self, query, context):
        """Запрос имени и фамилии пользователя"""
        user_id = query.from_user.id
        
        # Проверяем, есть ли уже активный пользователь
        if await self.check_user_has_vpn(user_id):
            await query.edit_message_text(
                "❌ У вас уже есть активный VPN аккаунт!\n\n"
                "Используйте /stats для просмотра статистики."
            )
            return
        
        # Сохраняем состояние - ожидаем ввод имени
        context.user_data['awaiting_name'] = True
        context.user_data['user_id'] = user_id
        
        await query.edit_message_text(
            "👤 Для создания VPN аккаунта, пожалуйста, введите ваше ФИО:\n\n"
            "• Имя и Фамилию (например: Иван Иванов)\n"
            "• Важно указать действительное ФИО, в противном случае VPN будет заблокирован\n\n"
            "📝 Это имя будет использовано при создании вашего профиля."
        )

    async def handle_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода имени пользователя"""
        if not context.user_data.get('awaiting_name'):
            return
        
        user_id = context.user_data.get('user_id')
        name_input = update.message.text.strip()
        
        # Проверяем валидность имени
        if not self.is_valid_name(name_input):
            await update.message.reply_text(
                "❌ Неверный формат имени!\n\n"
                "Пожалуйста, введите:\n"
                "• Имя и Фамилию (например: Иван Иванов)\n"
                "• Или любое удобное имя\n\n"
                "📝 Только буквы и пробелы, минимум 2 символа."
            )
            return
        
        # Очищаем состояние
        context.user_data['awaiting_name'] = False
        
        # Создаем email на основе имени
        email = self.create_email_from_name(name_input, user_id)
        
        # Сохраняем данные пользователя во временное хранилище
        self.user_data_cache[user_id] = {
            'name': name_input,
            'email': email,
            'username': update.effective_user.username or "unknown"
        }
        
        # Подтверждаем и создаем VPN
        await update.message.reply_text(
            f"✅ Отлично! Ваше имя: {name_input}\n"
            f"📧 Будет создан профиль: {email}\n\n"
            "🔄 Создаем ваш VPN аккаунт..."
        )
        
        # Создаем VPN пользователя
        await self.create_vpn_user_from_data(update, context, user_id)

    def is_valid_name(self, name: str) -> bool:
        """Проверяет валидность имени"""
        # Разрешаем буквы, пробелы, дефисы, апострофы
        if len(name) < 2 or len(name) > 50:
            return False
        
        # Проверяем что в имени есть только разрешенные символы
        pattern = r'^[a-zA-Zа-яА-ЯёЁ\s\-\.\']+$'
        return bool(re.match(pattern, name))

    def create_email_from_name(self, name: str, telegram_id: int) -> str:
        """Создает email на основе имени пользователя"""
        # Очищаем имя от лишних символов и приводим к нижнему регистру
        clean_name = re.sub(r'[^\w\s\-\.]', '', name)  # Удаляем специальные символы
        clean_name = clean_name.lower().strip()
        
        # Заменяем пробелы и точки на точки
        clean_name = re.sub(r'[\s\.]+', '.', clean_name)
        
        # Ограничиваем длину имени в email
        if len(clean_name) > 20:
            clean_name = clean_name[:20]
        
        # Создаем email
        email = f"{clean_name}@sayany.service"
        
        return email

    async def create_vpn_user_from_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Создание VPN пользователя с данными из кэша"""
        user_data = self.user_data_cache.get(user_id)
        
        if not user_data:
            await update.message.reply_text(
                "❌ Ошибка: данные пользователя не найдены.\n"
                "Пожалуйста, начните заново с команды /start"
            )
            return
        
        name = user_data['name']
        email = user_data['email']
        username = user_data['username']
        
        logging.info(f"🔄 Создание VPN для {name} ({email})")
        
        # Генерируем уникальный UUID для Xray
        xray_uuid = str(uuid.uuid4())
        logging.info(f"🔑 Сгенерирован UUID: {xray_uuid}")
        
        # Создаем пользователя в 3X-UI
        success = await self.create_xui_user(user_id, xray_uuid, email, name)
        
        if success:
            # Формируем конфиг для пользователя
            config = await self.generate_vless_config(xray_uuid, user_id)
            expires_at = datetime.now() + timedelta(days=30)
            
            await update.message.reply_text(
                f"✅ VPN аккаунт успешно создан!\n\n"
                f"👤 Имя: {name}\n"
                f"📧 Email: {email}\n"
                f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}\n"
                f"📊 Лимит трафика: 10 GB\n\n"
                f"🔧 Ваша конфигурация:\n"
                f"```\n{config}\n```\n\n"
                "📱 Скопируйте эту конфигурацию в ваш VPN клиент.",
                parse_mode='Markdown'
            )
            logging.info(f"✅ Пользователь {name} ({email}) успешно создан")
            
            # Очищаем кэш
            if user_id in self.user_data_cache:
                del self.user_data_cache[user_id]
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании VPN аккаунта!\n"
                "Попробуйте позже или свяжитесь с администратором."
            )
            logging.error(f"❌ Ошибка создания пользователя {name}")

    async def create_xui_user(self, telegram_id: int, uuid: str, email: str, name: str) -> bool:
        """Создание пользователя в 3X-UI через API с кастомным email"""
        try:
            # Получаем список инбоксов
            logging.info("📋 Получаем список инбоксов...")
            inboxes_response = self.session.get(f"{XUI_PANEL_URL}/panel/api/inbounds/list")
            
            if inboxes_response.status_code != 200:
                logging.error(f"❌ Ошибка получения инбоксов: {inboxes_response.status_code}")
                return False
            
            inboxes_data = inboxes_response.json()
            logging.info(f"📊 Получено инбоксов: {len(inboxes_data.get('obj', []))}")
            
            if not inboxes_data.get('obj'):
                logging.error("❌ Нет доступных инбоксов")
                return False
            
            # Берем ПЕРВЫЙ инбокс
            inbound = inboxes_data['obj'][0]
            inbound_id = inbound['id']
            inbound_remark = inbound.get('remark', 'Unknown')
            
            logging.info(f"🎯 Используем инбокс: {inbound_remark} (ID: {inbound_id})")
            
            # Формат данных для создания пользователя
            client_data = {
                "id": uuid,
                "flow": "xtls-rprx-vision", 
                "email": email,
                "limitIp": 0,
                "totalGB": 10737418240,  # 10GB
                "expiryTime": 0,
                "enable": True,
                "tgId": f"tg_{telegram_id}",
                "subId": "",
                "name": name  # Добавляем имя в заметки
            }
            
            request_data = {
                "id": inbound_id,
                "settings": json.dumps({"clients": [client_data]})
            }
            
            logging.info(f"📨 Отправляем запрос на создание пользователя с email: {email}")
            
            add_user_response = self.session.post(
                f"{XUI_PANEL_URL}/panel/api/inbounds/addClient",
                json=request_data
            )
            
            logging.info(f"📡 Ответ сервера: {add_user_response.status_code}")
            
            if add_user_response.status_code == 200:
                logging.info(f"✅ Пользователь {email} успешно создан в 3X-UI!")
                return True
            else:
                logging.error(f"❌ Ошибка создания пользователя: {add_user_response.status_code}")
                logging.error(f"📄 Текст ошибки: {add_user_response.text}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Исключение при создании пользователя: {e}")
            return False

    async def generate_vless_config(self, xray_uuid: str, telegram_user_id: int) -> str:
        """Генерация VLESS конфигурации с Reality"""
        params = {
            "type": "tcp",
            "headerType": "none",
            "flow": "xtls-rprx-vision",
            "security": "reality",
            "sni": "vk.com",
            "fp": "random",
            "pbk": REALITY_PUBLIC_KEY,
            "sid": REALITY_SHORT_ID
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        config = f"vless://{xray_uuid}@{SERVER_IP}:{SERVER_PORT}?{param_string}#TG_{telegram_user_id}"
        
        return config

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        user_id = update.effective_user.id
        
        # Получаем данные пользователя из 3X-UI
        user_data = await self.get_user_stats(user_id)
        
        if not user_data:
            await update.message.reply_text(
                "❌ У вас нет активного VPN аккаунта!\n\n"
                "Нажмите 'Создать VPN' чтобы начать использовать сервис."
            )
            return
        
        used_gb = user_data['used_traffic'] / (1024 ** 3)
        limit_gb = user_data['traffic_limit'] / (1024 ** 3)
        remaining_gb = limit_gb - used_gb
        progress_percent = (used_gb / limit_gb * 100) if limit_gb > 0 else 0
        
        await update.message.reply_text(
            f"📊 Ваша статистика:\n\n"
            f"👤 Пользователь: {user_data['email']}\n"
            f"📅 Создан: {user_data.get('created', 'N/A')}\n"
            f"📈 Использовано: {used_gb:.2f} GB\n"
            f"📉 Осталось: {remaining_gb:.2f} GB\n"
            f"📋 Лимит: {limit_gb:.2f} GB\n"
            f"📊 Прогресс: {progress_percent:.1f}%"
        )

    async def get_user_stats(self, telegram_id: int):
        """Получает статистику пользователя из 3X-UI"""
        try:
            users = await self.get_all_users_from_xui()
            for user in users:
                if f"tg{telegram_id}" in user['email']:
                    return {
                        'email': user['email'],
                        'traffic_limit': user['total_gb'],
                        'used_traffic': 0,  # 3X-UI API не предоставляет использованный трафик
                        'created': 'N/A'    # 3X-UI API не предоставляет дату создания
                    }
            return None
        except Exception as e:
            logging.error(f"Ошибка получения статистики: {e}")
            return None

    async def show_stats_callback(self, query, context):
        """Обработчик кнопки статистики"""
        user_id = query.from_user.id
        
        user_data = await self.get_user_stats(user_id)
        
        if not user_data:
            await query.edit_message_text(
                "❌ У вас нет активного VPN аккаунта!\n\n"
                "Нажмите 'Создать VPN' чтобы начать использовать сервис."
            )
            return
        
        used_gb = user_data['used_traffic'] / (1024 ** 3)
        limit_gb = user_data['traffic_limit'] / (1024 ** 3)
        remaining_gb = limit_gb - used_gb
        progress_percent = (used_gb / limit_gb * 100) if limit_gb > 0 else 0
        
        await query.edit_message_text(
            f"📊 Ваша статистика:\n\n"
            f"👤 Пользователь: {user_data['email']}\n"
            f"📅 Создан: {user_data.get('created', 'N/A')}\n"
            f"📈 Использовано: {used_gb:.2f} GB\n"
            f"📉 Осталось: {remaining_gb:.2f} GB\n"
            f"📋 Лимит: {limit_gb:.2f} GB\n"
            f"📊 Прогресс: {progress_percent:.1f}%"
        )

    async def delete_vpn_user(self, query, context):
        """Удаление VPN пользователя"""
        user_id = query.from_user.id
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_delete"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ ВНИМАНИЕ!\n\n"
            "Вы уверены, что хотите удалить ваш VPN аккаунт?\n\n"
            "Это действие:\n"
            "• Удалит вашу конфигурацию\n" 
            "• Очистит статистику\n"
            "• Не обратимо!\n\n"
            "После удаления вы сможете создать новый аккаунт.",
            reply_markup=reply_markup
        )

    async def confirm_delete_vpn(self, query, context):
        """Подтвержденное удаление VPN пользователя"""
        user_id = query.from_user.id
        
        try:
            success = await self.delete_xui_user(user_id)
            
            if success:
                await query.edit_message_text("✅ Ваш VPN аккаунт успешно удален!\n\nВы можете создать новый аккаунт в любое время.")
            else:
                await query.edit_message_text("❌ Ошибка при удалении VPN аккаунта!\nПопробуйте позже или свяжитесь с администратором.")
                
        except Exception as e:
            logging.error(f"Ошибка при удалении пользователя: {e}")
            await query.edit_message_text("❌ Произошла ошибка при удалении!\nПопробуйте позже или свяжитесь с администратором.")

    async def delete_xui_user(self, telegram_id: int) -> bool:
        """Удаление пользователя из 3X-UI через API"""
        try:
            users = await self.get_all_users_from_xui()
            
            for user in users:
                if f"tg{telegram_id}" in user['email']:
                    delete_response = self.session.post(
                        f"{XUI_PANEL_URL}/panel/api/inbounds/delClient/{user['inbound_id']}",
                        json={"email": user['email']}
                    )
                    return delete_response.status_code == 200
            
            return False
            
        except Exception as e:
            logging.error(f"Ошибка при удалении пользователя из 3X-UI: {e}")
            return False

    async def cancel_delete(self, query, context):
        """Отмена удаления"""
        await query.edit_message_text("❌ Удаление отменено.\n\nВаш VPN аккаунт сохранен.")

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🤖 Помощь по VPN боту

Доступные команды:
/start - Главное меню
/stats - Статистика трафика
/help - Эта справка

Как использовать:
1. Нажмите "Создать VPN" для создания аккаунта
2. Укажите ваше имя и фамилию
3. Скопируйте конфигурацию
4. Используйте в поддерживаемом клиенте

Поддерживаемые клиенты:
• v2rayNG (Android)
• Shadowrocket (iOS) 
• Qv2ray (Windows/Linux/Mac)

Проблемы?
Свяжитесь с администратором.
"""
        await update.message.reply_text(help_text)

    async def show_help_callback(self, query, context):
        """Обработчик кнопки помощи"""
        help_text = """
🤖 Помощь по VPN боту

Доступные команды:
/start - Главное меню  
/stats - Статистика трафика
/help - Эта справка

Как использовать:
1. Нажмите "Создать VPN" для создания аккаунта
2. Укажите ваше имя и фамилию
3. Скопируйте конфигурацию
4. Используйте в поддерживаемом клиенте

Поддерживаемые клиенты:
• v2rayNG (Android)
• Shadowrocket (iOS)
• Qv2ray (Windows/Linux/Mac)

Проблемы?
Свяжитесь с администратором.
"""
        await query.edit_message_text(help_text)

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика для администратора - данные из 3X-UI"""
        if update.effective_user.id != ADMIN_TELEGRAM_ID:
            await update.message.reply_text("❌ У вас нет прав для этой команды!")
            return
        
        try:
            users = await self.get_all_users_from_xui()
            
            if not users:
                await update.message.reply_text("❌ Не удалось получить данные из 3X-UI")
                return
            
            active_users = [u for u in users if u['enable']]
            total_traffic_limit = sum(u['total_gb'] for u in active_users) / (1024**3)
            
            message = (
                f"📈 Статистика администратора (из 3X-UI)\n\n"
                f"👥 Всего пользователей: {len(users)}\n"
                f"✅ Активных: {len(active_users)}\n"
                f"❌ Неактивных: {len(users) - len(active_users)}\n"
                f"📊 Общий лимит трафика: {total_traffic_limit:.1f} GB\n\n"
                f"📋 Последние пользователи:\n"
            )
            
            # Показываем последних 5 пользователей
            for i, user in enumerate(users[:5]):
                status = "✅" if user['enable'] else "❌"
                # Извлекаем имя из email
                name_part = user['email'].split('@')[0]
                message += f"{status} {name_part}\n"
            
            if len(users) > 5:
                message += f"\n... и еще {len(users) - 5} пользователей"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")

    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать всех пользователей из 3X-UI"""
        if update.effective_user.id != ADMIN_TELEGRAM_ID:
            await update.message.reply_text("❌ У вас нет прав для этой команды!")
            return
        
        try:
            users = await self.get_all_users_from_xui()
            
            if not users:
                await update.message.reply_text("❌ Нет пользователей в 3X-UI")
                return
            
            message = "👥 Все пользователи в 3X-UI:\n\n"
            
            for i, user in enumerate(users, 1):
                status = "✅" if user['enable'] else "❌"
                traffic_gb = user['total_gb'] / (1024**3) if user['total_gb'] else 0
                # Извлекаем имя из email для читаемости
                name_part = user['email'].split('@')[0]
                message += (
                    f"{i}. {status} {name_part}\n"
                    f"   📧 {user['email']}\n"
                    f"   🔑 {user['uuid'][:8]}...\n"
                    f"   📊 {traffic_gb:.1f} GB | {user['inbound']}\n\n"
                )
            
            # Если сообщение слишком длинное, разбиваем на части
            if len(message) > 4000:
                parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for part in parts:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(message)
                
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения пользователей: {e}")

def run_bot():
    """Запуск бота"""
    bot = VPNBot()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("stats", bot.show_stats))
    application.add_handler(CommandHandler("admin", bot.admin_stats))
    application.add_handler(CommandHandler("admin_users", bot.admin_users))
    application.add_handler(CommandHandler("help", bot.show_help))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Обработчик текстовых сообщений (для ввода имени)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_name_input))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logging.info("🤖 Бот запущен (с сбором имени пользователя)...")
    application.run_polling()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error(f"Exception while handling an update: {context.error}")
    
    try:
        if update and update.effective_user:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="❌ Произошла ошибка. Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        logging.error(f"Error in error handler: {e}")

if __name__ == '__main__':
    run_bot()