import asyncio
import asyncio
import sqlite3
import time
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

# Импорты для работы через прокси
from aiogram.client.session.aiohttp import AiohttpSession

# ==================== КОНСТАНТЫ ====================
API_TOKEN = '8549705364:AAFwhW7KExE9a-FkpMLS7PnDrlspx96TL1c'
ADMIN_ID = 6482609003 # Твой ID bnyk

# Инициализируем бота напрямую (на Render прокси НЕ НУЖНЫ)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== СОСТОЯНИЯ FSM ====================
class Form(StatesGroup):
    waiting_for_channel_link = State()
    waiting_for_subs_count = State()
    waiting_for_post_link = State()
    waiting_for_views_count = State()
    waiting_for_broadcast_text = State()
    waiting_for_setvip_id = State()

# Функция main для запуска (проверь, чтобы в конце файла было так же)
async def main():
    print("🤖 Бот запущен!")
    # Удаляем вебхук перед запуском, это часто решает проблемы с сетью
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка при запуске: {e}")

# Инициализируем бота ПЕРЕД диспетчером
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

# ==================== СОСТОЯНИЯ FSM ====================
class Form(StatesGroup):
    waiting_for_channel_link = State()
    waiting_for_subs_count = State()
    waiting_for_post_link = State()
    waiting_for_views_count = State()
    waiting_for_broadcast_text = State()
    waiting_for_setvip_id = State()
# Твой основной код продолжается ниже...

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            referrer_id INTEGER,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица заданий на подписку
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sub_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            channel_link TEXT,
            channel_id TEXT,
            remaining_count INTEGER,
            reward INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица заданий на просмотры
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS view_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            post_link TEXT,
            remaining_count INTEGER,
            reward INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица выполненных заданий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completed_tasks (
            user_id INTEGER,
            task_type TEXT,
            task_id INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, task_type, task_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id: int):
    """Получить пользователя или создать нового"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        # Создаем нового пользователя
        balance = 999999999 if user_id == ADMIN_ID else 0
        is_vip = 1 if user_id == ADMIN_ID else 0
        cursor.execute('INSERT INTO users (user_id, balance, is_vip) VALUES (?, ?, ?)',
                      (user_id, balance, is_vip))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    
    conn.close()
    return user

def update_balance(user_id: int, amount: int):
    """Обновить баланс пользователя"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def set_referrer(user_id: int, referrer_id: int):
    """Установить реферера"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET referrer_id = ? WHERE user_id = ? AND referrer_id IS NULL',
                  (referrer_id, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_top_users(limit: int = 10):
    """Получить топ пользователей по балансу"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ?', (limit,))
    users = cursor.fetchall()
    conn.close()
    return users

def set_vip(user_id: int):
    """Установить VIP статус"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_vip = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """Получить всех пользователей"""
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Заработать (Сабы/Глазки)", callback_data="earn")],
        [InlineKeyboardButton(text="📢 Продвинуть", callback_data="promote")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="🏆 ТОП", callback_data="top")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")]
    ])
    
    # Добавляем кнопку рассылки для админа
    return keyboard

def admin_menu_kb():
    """Меню с админскими кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Заработать (Сабы/Глазки)", callback_data="earn")],
        [InlineKeyboardButton(text="📢 Продвинуть", callback_data="promote")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="🏆 ТОП", callback_data="top")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="broadcast")]
    ])
    return keyboard

def earn_menu_kb():
    """Меню заработка"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Подписки (10 монет)", callback_data="earn_subs")],
        [InlineKeyboardButton(text="👀 Просмотры (2 монеты)", callback_data="earn_views")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])
    return keyboard

def promote_menu_kb():
    """Меню продвижения"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Продвинуть канал", callback_data="promote_channel")],
        [InlineKeyboardButton(text="📝 Продвинуть пост", callback_data="promote_post")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])
    return keyboard

def back_kb():
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])
    return keyboard

# ==================== HANDLERS ====================
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем реферальную ссылку
    if message.text and len(message.text.split()) > 1:
        try:
            ref_id = int(message.text.split()[1])
            if ref_id != user_id:
                # Проверяем, новый ли пользователь
                conn = sqlite3.connect('exchange.db')
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                existing = cursor.fetchone()
                conn.close()
                
                if not existing:
                    # Новый пользователь - устанавливаем реферера
                    get_user(user_id)  # Создаем пользователя
                    if set_referrer(user_id, ref_id):
                        update_balance(ref_id, 30)
                        try:
                            bot = message.bot
                            await bot.send_message(ref_id, "🎉 По вашей реферальной ссылке зарегистрировался новый пользователь! +30 монет")
                        except:
                            pass
        except ValueError:
            pass
    
    # Получаем или создаем пользователя
    get_user(user_id)
    
    welcome_text = f"👋 Добро пожаловать в биржу взаимного продвижения!\n\n" \
                   f"💰 Зарабатывайте монеты за подписки и просмотры\n" \
                   f"📢 Продвигайте свои каналы и посты\n" \
                   f"👥 Приглашайте друзей и получайте бонусы!"
    
    if user_id == ADMIN_ID:
        await message.answer(welcome_text, reply_markup=admin_menu_kb())
    else:
        await message.answer(welcome_text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    
    if user_id == ADMIN_ID:
        await callback.message.edit_text("🏠 Главное меню:", reply_markup=admin_menu_kb())
    else:
        await callback.message.edit_text("🏠 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "earn")
async def earn_menu(callback: CallbackQuery):
    """Меню заработка"""
    await callback.message.edit_text("💰 Выберите способ заработка:", reply_markup=earn_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "earn_subs")
async def earn_subs(callback: CallbackQuery):
    """Показать задания на подписки"""
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    # Получаем задания, которые пользователь еще не выполнял
    cursor.execute('''
        SELECT st.id, st.channel_link, st.channel_id, st.reward
        FROM sub_tasks st
        WHERE st.remaining_count > 0
        AND st.owner_id != ?
        AND NOT EXISTS (
            SELECT 1 FROM completed_tasks ct
            WHERE ct.user_id = ? AND ct.task_type = 'sub' AND ct.task_id = st.id
        )
        ORDER BY st.created_at DESC
        LIMIT 1
    ''', (user_id, user_id))
    
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        await callback.message.edit_text(
            "😔 Сейчас нет доступных заданий на подписки.\nПопробуйте позже!",
            reply_markup=back_kb()
        )
        await callback.answer()
        return
    
    task_id, channel_link, channel_id, reward = task
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=channel_link)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data=f"check_sub_{task_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn")]
    ])
    
    await callback.message.edit_text(
        f"👥 Задание на подписку\n\n"
        f"1️⃣ Подпишитесь на канал\n"
        f"2️⃣ Нажмите кнопку 'Проверить подписку'\n\n"
        f"💰 Награда: {reward} монет",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_sub_"))
async def check_subscription(callback: CallbackQuery):
    """Проверка подписки"""
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    # Получаем информацию о задании
    cursor.execute('SELECT channel_id, reward, remaining_count, owner_id FROM sub_tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    if not task:
        conn.close()
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    channel_id, reward, remaining_count, owner_id = task
    
    # Проверяем, не выполнял ли уже
    cursor.execute('SELECT 1 FROM completed_tasks WHERE user_id = ? AND task_type = ? AND task_id = ?',
                  (user_id, 'sub', task_id))
    if cursor.fetchone():
        conn.close()
        await callback.answer("❌ Вы уже выполнили это задание", show_alert=True)
        return
    
    # Проверяем подписку через API
    try:
        bot = callback.bot
        member = await bot.get_chat_member(channel_id, user_id)
        
        if member.status in ['member', 'administrator', 'creator']:
            # Подписка подтверждена
            cursor.execute('INSERT INTO completed_tasks (user_id, task_type, task_id) VALUES (?, ?, ?)',
                          (user_id, 'sub', task_id))
            cursor.execute('UPDATE sub_tasks SET remaining_count = remaining_count - 1 WHERE id = ?', (task_id,))
            conn.commit()
            
            update_balance(user_id, reward)
            
            conn.close()
            
            await callback.answer(f"✅ Подписка подтверждена! +{reward} монет", show_alert=True)
            
            # Переходим к следующему заданию
            await earn_subs(callback)
        else:
            conn.close()
            await callback.answer("❌ Вы не подписаны на канал", show_alert=True)
    except TelegramBadRequest as e:
        conn.close()
        if "chat not found" in str(e).lower():
            await callback.answer("❌ Бот не является администратором канала", show_alert=True)
        else:
            await callback.answer("❌ Не удалось проверить подписку", show_alert=True)
    except Exception as e:
        conn.close()
        await callback.answer("❌ Ошибка при проверке подписки", show_alert=True)

@router.callback_query(F.data == "earn_views")
async def earn_views(callback: CallbackQuery):
    """Показать задания на просмотры"""
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    # Получаем задания, которые пользователь еще не выполнял
    cursor.execute('''
        SELECT vt.id, vt.post_link, vt.reward
        FROM view_tasks vt
        WHERE vt.remaining_count > 0
        AND vt.owner_id != ?
        AND NOT EXISTS (
            SELECT 1 FROM completed_tasks ct
            WHERE ct.user_id = ? AND ct.task_type = 'view' AND ct.task_id = vt.id
        )
        ORDER BY vt.created_at DESC
        LIMIT 1
    ''', (user_id, user_id))
    
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        await callback.message.edit_text(
            "😔 Сейчас нет доступных заданий на просмотры.\nПопробуйте позже!",
            reply_markup=back_kb()
        )
        await callback.answer()
        return
    
    task_id, post_link, reward = task
    current_time = int(time.time())
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Посмотреть пост", url=post_link)],
        [InlineKeyboardButton(text="✅ Проверить просмотр", callback_data=f"check_view_{task_id}_{current_time}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn")]
    ])
    
    await callback.message.edit_text(
        f"👀 Задание на просмотр\n\n"
        f"1️⃣ Перейдите по ссылке и посмотрите пост\n"
        f"2️⃣ Подождите 2 секунды\n"
        f"3️⃣ Нажмите кнопку 'Проверить просмотр'\n\n"
        f"💰 Награда: {reward} монет",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_view_"))
async def check_view(callback: CallbackQuery):
    """Проверка просмотра"""
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    task_id = int(parts[2])
    start_time = int(parts[3])
    current_time = int(time.time())
    
    # Проверяем, прошло ли 2 секунды
    if current_time - start_time < 2:
        await callback.answer("⏳ Подождите минимум 2 секунды", show_alert=True)
        return
    
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    # Получаем информацию о задании
    cursor.execute('SELECT reward, remaining_count FROM view_tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    if not task:
        conn.close()
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    reward, remaining_count = task
    
    # Проверяем, не выполнял ли уже
    cursor.execute('SELECT 1 FROM completed_tasks WHERE user_id = ? AND task_type = ? AND task_id = ?',
                  (user_id, 'view', task_id))
    if cursor.fetchone():
        conn.close()
        await callback.answer("❌ Вы уже выполнили это задание", show_alert=True)
        return
    
    # Засчитываем просмотр
    cursor.execute('INSERT INTO completed_tasks (user_id, task_type, task_id) VALUES (?, ?, ?)',
                  (user_id, 'view', task_id))
    cursor.execute('UPDATE view_tasks SET remaining_count = remaining_count - 1 WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    
    update_balance(user_id, reward)
    
    await callback.answer(f"✅ Просмотр засчитан! +{reward} монет", show_alert=True)
    
    # Переходим к следующему заданию
    await earn_views(callback)

@router.callback_query(F.data == "promote")
async def promote_menu_handler(callback: CallbackQuery):
    """Меню продвижения"""
    await callback.message.edit_text("📢 Выберите тип продвижения:", reply_markup=promote_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "promote_channel")
async def promote_channel(callback: CallbackQuery, state: FSMContext):
    """Продвижение канала"""
    await callback.message.edit_text(
        "📢 Продвижение канала\n\n"
        "Отправьте ссылку на ваш канал (например: https://t.me/yourchannel)\n\n"
        "❗️ Важно: добавьте бота в администраторы канала!",
        reply_markup=back_kb()
    )
    await state.set_state(Form.waiting_for_channel_link)
    await callback.answer()

@router.message(Form.waiting_for_channel_link)
async def process_channel_link(message: Message, state: FSMContext):
    """Обработка ссылки на канал"""
    channel_link = message.text.strip()
    
    # Проверяем формат ссылки
    if not channel_link.startswith("https://t.me/"):
        await message.answer("❌ Неверный формат ссылки. Используйте формат: https://t.me/yourchannel")
        return
    
    # Извлекаем username канала
    channel_username = channel_link.split("/")[-1]
    
    # Проверяем, является ли бот админом
    try:
        bot = message.bot
        chat = await bot.get_chat(f"@{channel_username}")
        channel_id = chat.id
        
        bot_member = await bot.get_chat_member(channel_id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await message.answer("❌ Бот не является администратором канала. Добавьте бота в администраторы!")
            return
    except Exception as e:
        await message.answer(f"❌ Не удалось получить доступ к каналу. Проверьте ссылку и права бота.")
        return
    
    await state.update_data(channel_link=channel_link, channel_id=str(channel_id))
    await message.answer(
        "✅ Канал найден!\n\n"
        "Сколько подписчиков хотите получить?\n"
        "💰 Стоимость: 15 монет за 1 подписчика"
    )
    await state.set_state(Form.waiting_for_subs_count)

@router.message(Form.waiting_for_subs_count)
async def process_subs_count(message: Message, state: FSMContext):
    """Обработка количества подписчиков"""
    try:
        count = int(message.text.strip())
        if count <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return
    
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = user[1]
    
    cost = count * 15
    
    if balance < cost:
        await message.answer(f"❌ Недостаточно монет!\n\nНужно: {cost} монет\nУ вас: {balance} монет")
        await state.clear()
        return
    
    # Снимаем монеты
    update_balance(user_id, -cost)
    
    # Создаем задание
    data = await state.get_data()
    channel_link = data['channel_link']
    channel_id = data['channel_id']
    
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sub_tasks (owner_id, channel_link, channel_id, remaining_count)
        VALUES (?, ?, ?, ?)
    ''', (user_id, channel_link, channel_id, count))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ Задание создано!\n\n"
        f"📢 Канал: {channel_link}\n"
        f"👥 Подписчиков: {count}\n"
        f"💰 Потрачено: {cost} монет\n\n"
        f"Подписчики начнут приходить в ближайшее время!",
        reply_markup=back_kb()
    )
    await state.clear()

@router.callback_query(F.data == "promote_post")
async def promote_post(callback: CallbackQuery, state: FSMContext):
    """Продвижение поста"""
    await callback.message.edit_text(
        "📝 Продвижение поста\n\n"
        "Отправьте ссылку на ваш пост (например: https://t.me/yourchannel/123)",
        reply_markup=back_kb()
    )
    await state.set_state(Form.waiting_for_post_link)
    await callback.answer()

@router.message(Form.waiting_for_post_link)
async def process_post_link(message: Message, state: FSMContext):
    """Обработка ссылки на пост"""
    post_link = message.text.strip()
    
    # Проверяем формат ссылки
    if not post_link.startswith("https://t.me/") or "/" not in post_link[13:]:
        await message.answer("❌ Неверный формат ссылки. Используйте формат: https://t.me/channel/123")
        return
    
    await state.update_data(post_link=post_link)
    await message.answer(
        "✅ Ссылка принята!\n\n"
        "Сколько просмотров хотите получить?\n"
        "💰 Стоимость: 3 монеты за 1 просмотр"
    )
    await state.set_state(Form.waiting_for_views_count)

@router.message(Form.waiting_for_views_count)
async def process_views_count(message: Message, state: FSMContext):
    """Обработка количества просмотров"""
    try:
        count = int(message.text.strip())
        if count <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return
    
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = user[1]
    
    cost = count * 3
    
    if balance < cost:
        await message.answer(f"❌ Недостаточно монет!\n\nНужно: {cost} монет\nУ вас: {balance} монет")
        await state.clear()
        return
    
    # Снимаем монеты
    update_balance(user_id, -cost)
    
    # Создаем задание
    data = await state.get_data()
    post_link = data['post_link']
    
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO view_tasks (owner_id, post_link, remaining_count)
        VALUES (?, ?, ?)
    ''', (user_id, post_link, count))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ Задание создано!\n\n"
        f"📝 Пост: {post_link}\n"
        f"👀 Просмотров: {count}\n"
        f"💰 Потрачено: {cost} монет\n\n"
        f"Просмотры начнут приходить в ближайшее время!",
        reply_markup=back_kb()
    )
    await state.clear()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    balance = user[1]
    is_vip = user[2]
    
    status = "⭐️ VIP" if is_vip else "👤 Обычный"
    
    profile_text = (
        f"👤 Ваш профиль\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Баланс: {balance} монет\n"
        f"📊 Статус: {status}"
    )
    
    await callback.message.edit_text(profile_text, reply_markup=back_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "top")
async def show_top(callback: CallbackQuery):
    """Показать ТОП-10"""
    top_users = get_top_users(10)
    
    if not top_users:
        await callback.message.edit_text("📊 ТОП пользователей пока пуст", reply_markup=back_kb())
        await callback.answer()
        return
    
    top_text = "🏆 ТОП-10 пользователей по балансу:\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, balance) in enumerate(top_users, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        top_text += f"{medal} ID: {uid} — {balance} монет\n"
    
    await callback.message.edit_text(top_text, reply_markup=back_kb())
    await callback.answer()

@router.callback_query(F.data == "referrals")
async def show_referrals(callback: CallbackQuery):
    """Показать реферальную систему"""
    user_id = callback.from_user.id
    bot_username = (await callback.bot.get_me()).username
    
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    # Считаем рефералов
    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
    ref_count = cursor.fetchone()[0]
    conn.close()
    
    ref_text = (
        f"👥 Реферальная программа\n\n"
        f"💰 Получайте 30 монет за каждого приглашенного друга!\n\n"
        f"👤 Ваших рефералов: {ref_count}\n\n"
        f"🔗 Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"Или нажмите: <a href='{ref_link}'>Пригласить друга</a>"
    )
    
    await callback.message.edit_text(ref_text, reply_markup=back_kb(), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

# ==================== АДМИН-ФУНКЦИИ ====================
@router.message(Command("setvip"))
async def cmd_setvip(message: Message, state: FSMContext):
    """Команда установки VIP"""
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) == 2:
        try:
            target_id = int(parts[1])
            set_vip(target_id)
            await message.answer(f"✅ VIP статус установлен для пользователя {target_id}")
        except ValueError:
            await message.answer("❌ Неверный ID пользователя")
    else:
        await message.answer("📝 Отправьте ID пользователя для выдачи VIP:")
        await state.set_state(Form.waiting_for_setvip_id)

@router.message(Form.waiting_for_setvip_id)
async def process_setvip_id(message: Message, state: FSMContext):
    """Обработка ID для VIP"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        target_id = int(message.text.strip())
        set_vip(target_id)
        await message.answer(f"✅ VIP статус установлен для пользователя {target_id}")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный ID пользователя")

@router.callback_query(F.data == "broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступно только администратору", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📨 Рассылка\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям:",
        reply_markup=back_kb()
    )
    await state.set_state(Form.waiting_for_broadcast_text)
    await callback.answer()

@router.message(Form.waiting_for_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    broadcast_text = message.text
    users = get_all_users()
    
    success = 0
    failed = 0
    
    status_msg = await message.answer(f"📨 Начинаю рассылку...\n\n👥 Всего пользователей: {len(users)}")
    
    for user_id in users:
        try:
            await message.bot.send_message(user_id, broadcast_text)
            success += 1
            await asyncio.sleep(0.05)  # Задержка для избежания лимитов
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}"
    )
    await state.clear()

# ==================== MAIN ====================
async def main():
    # Инициализация БД
    init_db()
    
    # Инициализация бота
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация роутера
    dp.include_router(router)
    
    # Запуск
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
    except Exception as e:
        print(f"Ошибка: {e}")
