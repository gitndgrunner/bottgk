import logging
import random
import json
import os
import string
from typing import Dict
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
import asyncio
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

API_TOKEN = '8403703022:AAHGkmD5ZoAD2AF0J3ajlfBH7_eN9vwLNpU'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Константы для файлов
USERS_DB_FILE = 'users_db.json'
ADMIN_DB_FILE = 'admin_db.json'
WIN_CODES_DB_FILE = 'win_codes_db.json'
LOG_FILE = 'bot_logs.txt'

# ID канала, на который нужно подписаться (замените на ваш)
CHANNEL_ID = -1002686886872
CHANNEL_LINK = "https://t.me/Basketball_Gifts"

# База данных пользователей
users_db: Dict[int, Dict] = {}
admin_db = {
    'stars_balance': 0,
    'settings': {
        'ball1_cost': 5,
        'ball2_cost': 3,
        'ball3_cost': 1,
        'ball1_chance': 0.2,
        'ball2_chance': 0.4,
        'ball3_chance': 0.6,
        'min_withdraw': 50
    }
}

# База данных выигрышных кодов
win_codes_db = {}

# Загрузка данных из файлов при старте
def load_data():
    global users_db, admin_db, win_codes_db
    
    try:
        if os.path.exists(USERS_DB_FILE):
            with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
                users_db = json.load(f)
                users_db = {int(k): v for k, v in users_db.items()}
                log_event("SYSTEM", f"Загружены данные пользователей из {USERS_DB_FILE}")
    except Exception as e:
        log_event("SYSTEM", f"Ошибка загрузки users_db: {str(e)}")
        users_db = {}

    try:
        if os.path.exists(ADMIN_DB_FILE):
            with open(ADMIN_DB_FILE, 'r', encoding='utf-8') as f:
                admin_db = json.load(f)
                log_event("SYSTEM", f"Загружены данные админа из {ADMIN_DB_FILE}")
    except Exception as e:
        log_event("SYSTEM", f"Ошибка загрузки admin_db: {str(e)}")
        admin_db = {
            'stars_balance': 0,
            'settings': {
                'ball1_cost': 5,
                'ball2_cost': 3,
                'ball3_cost': 1,
                'ball1_chance': 0.2,
                'ball2_chance': 0.4,
                'ball3_chance': 0.6,
                'min_withdraw': 50
            }
        }
    
    try:
        if os.path.exists(WIN_CODES_DB_FILE):
            with open(WIN_CODES_DB_FILE, 'r', encoding='utf-8') as f:
                win_codes_db = json.load(f)
                log_event("SYSTEM", f"Загружены коды выигрышей из {WIN_CODES_DB_FILE}")
    except Exception as e:
        log_event("SYSTEM", f"Ошибка загрузки win_codes_db: {str(e)}")
        win_codes_db = {}

# Функция для сохранения данных
def save_data():
    try:
        with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_db, f, ensure_ascii=False, indent=4)
        
        with open(ADMIN_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(admin_db, f, ensure_ascii=False, indent=4)
            
        with open(WIN_CODES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(win_codes_db, f, ensure_ascii=False, indent=4)
            
        log_event("SYSTEM", "Данные успешно сохранены")
    except Exception as e:
        log_event("SYSTEM", f"Ошибка сохранения данных: {str(e)}")

# Функция для логирования событий
def log_event(user_id: str, event: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] UserID: {user_id} - {event}\n"
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Ошибка записи в лог: {str(e)}")

# Генерация случайного кода
def generate_win_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Состояния для FSM
class PaymentState(StatesGroup):
    waiting_for_custom_amount = State()
    waiting_for_admin_password = State()
    waiting_for_settings_change = State()
    waiting_for_withdraw_amount = State()
    waiting_for_user_id = State()
    waiting_for_stars_amount = State()
    waiting_for_win_code = State()

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Играть")],
            [KeyboardButton(text="💰 Пополнить баланс")],
            [KeyboardButton(text="📊 Статистика")]
        ],
        resize_keyboard=True
    )

def get_game_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"1 мяч ({admin_db['settings']['ball1_cost']}⭐)")],
            [KeyboardButton(text=f"2 мяча ({admin_db['settings']['ball2_cost']}⭐)")],
            [KeyboardButton(text=f"3 мяча ({admin_db['settings']['ball3_cost']}⭐)")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_payment_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="5⭐"), KeyboardButton(text="10⭐")],
            [KeyboardButton(text="100⭐")],
            [KeyboardButton(text="Другая сумма")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс бота")],
            [KeyboardButton(text="⚙ Настройки игры")],
            [KeyboardButton(text="👤 Управление пользователями")],
            [KeyboardButton(text="📤 Вывести звёзды")],
            [KeyboardButton(text="📊 Логи пользователей")],
            [KeyboardButton(text="🔍 Проверить выигрышный код")],
            [KeyboardButton(text="💾 Сохранить данные")],
            [KeyboardButton(text="🔙 Выйти из админки")]
        ],
        resize_keyboard=True
    )

def get_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏ Стоимость 1 мяча")],
            [KeyboardButton(text="✏ Стоимость 2 мячей")],
            [KeyboardButton(text="✏ Стоимость 3 мячей")],
            [KeyboardButton(text="✏ Шанс 1 мяча")],
            [KeyboardButton(text="✏ Шанс 2 мячей")],
            [KeyboardButton(text="✏ Шанс 3 мячей")],
            [KeyboardButton(text="✏ Мин. вывод")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_user_management_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить звёзд")],
            [KeyboardButton(text="➖ Убрать звёзд")],
            [KeyboardButton(text="🚫 Заблокировать")],
            [KeyboardButton(text="✅ Разблокировать")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

@dp.message(Command("start", "help"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Я подписался", callback_data="check_subscription")]
        ])
        await message.answer(
            "📢 Для использования бота необходимо подписаться на наш канал!\n\n"
            "После подписки нажмите кнопку 'Я подписался'",
            reply_markup=keyboard
        )
        return
    
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': 100, 
            'games_played': 0, 
            'games_won': 0,
            'is_blocked': False,
            'win_codes': []
        }
        log_event(user_id, "Новый пользователь. Начислен стартовый бонус 100⭐")
    
    if users_db[user_id].get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    await message.answer(
        "🏀 Добро пожаловать в баскетбольную игру!\n\n"
        "Правила:\n"
        f"- 1 мяч за {admin_db['settings']['ball1_cost']}⭐ (победа: 1/1)\n"
        f"- 2 мяча за {admin_db['settings']['ball2_cost']}⭐ (победа: 2/2)\n"
        f"- 3 мяча за {admin_db['settings']['ball3_cost']}⭐ (победа: 3/3)\n\n"
        f"🎁 Вам начислен стартовый бонус: 100⭐\n"
        "Если выигрываете - получаете приз и уникальный код!",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "check_subscription")
async def process_check_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback_query.message.delete()
        
        if user_id not in users_db:
            users_db[user_id] = {
                'balance': 100, 
                'games_played': 0, 
                'games_won': 0,
                'is_blocked': False,
                'win_codes': []
            }
            log_event(user_id, "Новый пользователь. Начислен стартовый бонус 100⭐")
        
        await callback_query.message.answer(
            "🏀 Добро пожаловать в баскетбольную игру!\n\n"
            "Правила:\n"
            f"- 1 мяч за {admin_db['settings']['ball1_cost']}⭐ (победа: 1/1)\n"
            f"- 2 мяча за {admin_db['settings']['ball2_cost']}⭐ (победа: 2/2)\n"
            f"- 3 мяча за {admin_db['settings']['ball3_cost']}⭐ (победа: 3/3)\n\n"
            f"🎁 Вам начислен стартовый бонус: 100⭐\n"
            "Если выигрываете - получаете приз и уникальный код!",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback_query.answer("❌ Вы ещё не подписались на канал!", show_alert=True)

@dp.message(Command("adminpanel"))
async def admin_panel(message: types.Message, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_admin_password)
    await message.answer("Введите пароль для доступа к админ-панели:")

@dp.message(lambda message: message.text == "🔙 Назад")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню", reply_markup=get_main_keyboard())

@dp.message(lambda message: message.text == "🔙 Выйти из админки")
async def exit_admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вышли из админ-панели", reply_markup=get_main_keyboard())

@dp.message(lambda message: message.text == "🎮 Играть")
async def play_game(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Я подписался", callback_data="check_subscription")]
        ])
        await message.answer(
            "📢 Для использования бота необходимо подписаться на наш канал!\n\n"
            "После подписки нажмите кнопку 'Я подписался'",
            reply_markup=keyboard
        )
        return
    
    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    await message.answer("Выберите вариант игры:", reply_markup=get_game_keyboard())

@dp.message(lambda message: message.text == "💰 Пополнить баланс")
async def add_balance(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Я подписался", callback_data="check_subscription")]
        ])
        await message.answer(
            "📢 Для использования бота необходимо подписаться на наш канал!\n\n"
            "После подписки нажмите кнопку 'Я подписался'",
            reply_markup=keyboard
        )
        return

    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    await message.answer("Выберите сумму пополнения:", reply_markup=get_payment_keyboard())

@dp.message(lambda message: message.text == "📊 Статистика")
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Я подписался", callback_data="check_subscription")]
        ])
        await message.answer(
            "📢 Для использования бота необходимо подписаться на наш канал!\n\n"
            "После подписки нажмите кнопку 'Я подписался'",
            reply_markup=keyboard
        )
        return
        
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': 100, 
            'games_played': 0, 
            'games_won': 0,
            'is_blocked': False,
            'win_codes': []
        }
    
    stats = users_db[user_id]
    await message.answer(
        f"📊 Ваша статистика:\n\n"
        f"🆔 ID пользователя: {user_id}\n"
        f"💰 Баланс: {stats['balance']}⭐\n"
        f"🎮 Игр сыграно: {stats['games_played']}\n"
        f"🏆 Игр выиграно: {stats['games_won']}\n"
        f"🔑 Кодов выигрыша: {len(stats.get('win_codes', []))}"
    )

@dp.message(lambda message: message.text.startswith("1 мяч"))
async def play_one_ball(message: types.Message):
    user_id = message.from_user.id
    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': 100, 
            'games_played': 0, 
            'games_won': 0,
            'is_blocked': False,
            'win_codes': []
        }
    
    user_data = users_db[user_id]
    cost = admin_db['settings']['ball1_cost']
    if user_data['balance'] < cost:
        await message.answer(f"❌ Недостаточно звёзд для игры! Пополните баланс.")
        log_event(user_id, f"Попытка игры в 1 мяч (недостаточно средств)")
        return
    
    await message.answer("🏀")
    
    user_data['balance'] -= cost
    admin_db['stars_balance'] += cost
    user_data['games_played'] += 1
    
    log_event(user_id, f"Списано {cost}⭐ за игру в 1 мяч. Баланс: {user_data['balance']}⭐")
    
    await asyncio.sleep(2)
    
    hits = 1 if random.random() < admin_db['settings']['ball1_chance'] else 0
    
    if hits == 1:
        user_data['games_won'] += 1
        win_code = generate_win_code()
        user_data['win_codes'].append(win_code)
        win_codes_db[win_code] = {
            'user_id': user_id,
            'game_type': "1 мяч",
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'used': False
        }
        await message.answer(
            "🏆 Поздравляем! Вы попали и выиграли приз!\n"
            f"🔑 Ваш код выигрыша: {win_code}\n"
            "Сохраните этот код для получения приза!"
        )
        log_event(user_id, f"Выигрыш в игре 1 мяч. Код: {win_code}")
    else:
        await message.answer("❌ Мяч не попал в корзину. Попробуйте ещё раз!")
        log_event(user_id, "Проигрыш в игре 1 мяч")
    
    await show_stats(message)
    save_data()

@dp.message(lambda message: message.text.startswith("2 мяча"))
async def play_two_balls(message: types.Message):
    user_id = message.from_user.id
    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': 100, 
            'games_played': 0, 
            'games_won': 0,
            'is_blocked': False,
            'win_codes': []
        }
    
    user_data = users_db[user_id]
    cost = admin_db['settings']['ball2_cost']
    if user_data['balance'] < cost:
        await message.answer(f"❌ Недостаточно звёзд для игры! Пополните баланс.")
        log_event(user_id, f"Попытка игры в 2 мяча (недостаточно средств)")
        return
    
    user_data['balance'] -= cost
    admin_db['stars_balance'] += cost
    user_data['games_played'] += 1
    
    log_event(user_id, f"Списано {cost}⭐ за игру в 2 мяча. Баланс: {user_data['balance']}⭐")
    
    hits = 0
    
    for i in range(2):
        await message.answer("🏀")
        await asyncio.sleep(1.5)
        
        if random.random() < admin_db['settings']['ball2_chance']:
            hits += 1
            await message.answer("✅ Попал!")
        else:
            await message.answer("❌ Промах!")
        await asyncio.sleep(0.5)
    
    if hits == 2:
        user_data['games_won'] += 1
        win_code = generate_win_code()
        user_data['win_codes'].append(win_code)
        win_codes_db[win_code] = {
            'user_id': user_id,
            'game_type': "2 мяча",
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'used': False
        }
        await message.answer(
            "🏆 Поздравляем! Вы попали оба мяча и выиграли приз!\n"
            f"🔑 Ваш код выигрыша: {win_code}\n"
            "Сохраните этот код для получения приза!"
        )
        log_event(user_id, f"Выигрыш в игре 2 мяча. Код: {win_code}")
    else:
        await message.answer(f"❌ Вы попали только {hits} из 2 мячей. Попробуйте ещё раз!")
        log_event(user_id, f"Проигрыш в игре 2 мяча (попаданий: {hits})")
    
    await show_stats(message)
    save_data()

@dp.message(lambda message: message.text.startswith("3 мяча"))
async def play_three_balls(message: types.Message):
    user_id = message.from_user.id
    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': 100, 
            'games_played': 0, 
            'games_won': 0,
            'is_blocked': False,
            'win_codes': []
        }
    
    user_data = users_db[user_id]
    cost = admin_db['settings']['ball3_cost']
    if user_data['balance'] < cost:
        await message.answer(f"❌ Недостаточно звёзд для игры! Пополните баланс.")
        log_event(user_id, f"Попытка игры в 3 мяча (недостаточно средств)")
        return
    
    user_data['balance'] -= cost
    admin_db['stars_balance'] += cost
    user_data['games_played'] += 1
    
    log_event(user_id, f"Списано {cost}⭐ за игру в 3 мяча. Баланс: {user_data['balance']}⭐")
    
    hits = 0
    
    for i in range(3):
        await message.answer("🏀")
        await asyncio.sleep(1.5)
        
        if random.random() < admin_db['settings']['ball3_chance']:
            hits += 1
            await message.answer("✅ Попал!")
        else:
            await message.answer("❌ Промах!")
        await asyncio.sleep(0.5)
    
    if hits == 3:
        user_data['games_won'] += 1
        win_code = generate_win_code()
        user_data['win_codes'].append(win_code)
        win_codes_db[win_code] = {
            'user_id': user_id,
            'game_type': "3 мяча",
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'used': False
        }
        await message.answer(
            "🏆 Поздравляем! Вы попали все 3 мяча и выиграли приз!\n"
            f"🔑 Ваш код выигрыша: {win_code}\n"
            "Сохраните этот код для получения приза!"
        )
        log_event(user_id, f"Выигрыш в игре 3 мяча. Код: {win_code}")
    else:
        await message.answer(f"❌ Вы попали только {hits} из 3 мячей. Попробуйте ещё раз!")
        log_event(user_id, f"Проигрыш в игре 3 мяча (попаданий: {hits})")
    
    await show_stats(message)
    save_data()

@dp.message(lambda message: message.text in ["5⭐", "10⭐", "100⭐"])
async def process_payment(message: types.Message):
    amount = int(message.text.replace("⭐", ""))
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить звёздами", pay=True)],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_payment")]
    ])
    
    log_event(user_id, f"Запрошено пополнение на {amount}⭐")
    
    await message.answer(
        f"Для пополнения баланса на {amount}⭐ нажмите кнопку ниже:",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "Другая сумма")
async def custom_amount(message: types.Message, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_custom_amount)
    await message.answer("Введите желаемую сумму пополнения (целое число):")

@dp.message(PaymentState.waiting_for_custom_amount)
async def process_custom_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
        
        user_id = message.from_user.id
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить звёздами", pay=True)],
            [InlineKeyboardButton(text="Отменить", callback_data="cancel_payment")]
        ])
        
        log_event(user_id, f"Запрошено пополнение на {amount}⭐ (пользовательский ввод)")
        
        await message.answer(
            f"Для пополнения баланса на {amount}⭐ нажмите кнопку ниже:",
            reply_markup=keyboard
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму (целое положительное число).")
        return
    await state.clear()

@dp.message(PaymentState.waiting_for_admin_password)
async def check_admin_password(message: types.Message, state: FSMContext):
    if message.text == "807807":
        await state.set_state(None)
        await message.answer("Добро пожаловать в админ-панель!", reply_markup=get_admin_keyboard())
        log_event(message.from_user.id, "Вход в админ-панель")
    else:
        await message.answer("❌ Неверный пароль! Попробуйте ещё раз.")
        log_event(message.from_user.id, f"Неудачная попытка входа в админ-панель (пароль: {message.text})")

@dp.message(lambda message: message.text == "💰 Баланс бота")
async def show_bot_balance(message: types.Message):
    await message.answer(f"💰 Баланс бота: {admin_db['stars_balance']}⭐")
    log_event(message.from_user.id, "Просмотр баланса бота")

@dp.message(lambda message: message.text == "⚙ Настройки игры")
async def game_settings(message: types.Message):
    settings = admin_db['settings']
    text = (
        f"⚙ Текущие настройки игры:\n\n"
        f"1 мяч: {settings['ball1_cost']}⭐ (шанс: {settings['ball1_chance']*100}%)\n"
        f"2 мяча: {settings['ball2_cost']}⭐ (шанс: {settings['ball2_chance']*100}%)\n"
        f"3 мяча: {settings['ball3_cost']}⭐ (шанс: {settings['ball3_chance']*100}%)\n"
        f"Мин. вывод: {settings['min_withdraw']}⭐"
    )
    await message.answer(text, reply_markup=get_settings_keyboard())
    log_event(message.from_user.id, "Просмотр настроек игры")

@dp.message(lambda message: message.text.startswith("✏"))
async def change_setting(message: types.Message, state: FSMContext):
    setting_map = {
        "✏ Стоимость 1 мяча": "ball1_cost",
        "✏ Стоимость 2 мячей": "ball2_cost",
        "✏ Стоимость 3 мячей": "ball3_cost",
        "✏ Шанс 1 мяча": "ball1_chance",
        "✏ Шанс 2 мячей": "ball2_chance",
        "✏ Шанс 3 мячей": "ball3_chance",
        "✏ Мин. вывод": "min_withdraw"
    }
    
    setting_name = setting_map.get(message.text)
    if setting_name:
        await state.set_state(PaymentState.waiting_for_settings_change)
        await state.update_data(setting_name=setting_name)
        await message.answer(f"Введите новое значение для {message.text[2:]}:")
        log_event(message.from_user.id, f"Запрос на изменение настройки: {setting_name}")
    else:
        await message.answer("Неизвестная настройка")

@dp.message(PaymentState.waiting_for_settings_change)
async def save_setting_change(message: types.Message, state: FSMContext):
    data = await state.get_data()
    setting_name = data.get('setting_name')
    
    try:
        if setting_name in ['ball1_chance', 'ball2_chance', 'ball3_chance']:
            value = float(message.text)
            if not 0 <= value <= 1:
                raise ValueError
        else:
            value = int(message.text)
            if value <= 0:
                raise ValueError
        
        old_value = admin_db['settings'][setting_name]
        admin_db['settings'][setting_name] = value
        await message.answer("✅ Настройка успешно изменена!", reply_markup=get_admin_keyboard())
        log_event(message.from_user.id, f"Изменение настройки {setting_name}: {old_value} -> {value}")
    except ValueError:
        await message.answer("❌ Некорректное значение! Введите число (для шанса - дробное от 0 до 1)")
        return
    
    await state.clear()
    save_data()

@dp.message(lambda message: message.text == "👤 Управление пользователями")
async def user_management(message: types.Message, state: FSMContext):
    await message.answer("Выберите действие:", reply_markup=get_user_management_keyboard())

@dp.message(lambda message: message.text in ["➕ Добавить звёзд", "➖ Убрать звёзд"])
async def manage_user_stars(message: types.Message, state: FSMContext):
    action = "add" if message.text == "➕ Добавить звёзд" else "remove"
    await state.set_state(PaymentState.waiting_for_user_id)
    await state.update_data(action=action)
    await message.answer("Введите ID пользователя:")

@dp.message(PaymentState.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        data = await state.get_data()
        await state.update_data(user_id=user_id)
        await state.set_state(PaymentState.waiting_for_stars_amount)
        await message.answer(f"Введите количество звёзд для {'добавления' if data['action'] == 'add' else 'удаления'}:")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID пользователя (число)")

@dp.message(PaymentState.waiting_for_stars_amount)
async def process_stars_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
        
        data = await state.get_data()
        user_id = data['user_id']
        action = data['action']
        
        if user_id not in users_db:
            users_db[user_id] = {
                'balance': 0, 
                'games_played': 0, 
                'games_won': 0,
                'is_blocked': False,
                'win_codes': []
            }
        
        if action == "add":
            users_db[user_id]['balance'] += amount
            admin_db['stars_balance'] -= amount
            log_event(message.from_user.id, f"Добавлено {amount}⭐ пользователю {user_id}")
            await message.answer(f"✅ Пользователю {user_id} добавлено {amount}⭐")
        else:
            if users_db[user_id]['balance'] >= amount:
                users_db[user_id]['balance'] -= amount
                admin_db['stars_balance'] += amount
                log_event(message.from_user.id, f"Удалено {amount}⭐ у пользователя {user_id}")
                await message.answer(f"✅ У пользователя {user_id} удалено {amount}⭐")
            else:
                await message.answer(f"❌ У пользователя недостаточно звёзд. Текущий баланс: {users_db[user_id]['balance']}⭐")
        
        save_data()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное количество звёзд (положительное число)")
    finally:
        await state.clear()

@dp.message(lambda message: message.text in ["🚫 Заблокировать", "✅ Разблокировать"])
async def manage_user_block(message: types.Message, state: FSMContext):
    action = "block" if message.text == "🚫 Заблокировать" else "unblock"
    await state.set_state(PaymentState.waiting_for_user_id)
    await state.update_data(action=action)
    await message.answer("Введите ID пользователя:")

@dp.message(lambda message: message.text == "📤 Вывести звёзды")
async def withdraw_stars(message: types.Message, state: FSMContext):
    if admin_db['stars_balance'] < admin_db['settings']['min_withdraw']:
        await message.answer(
            f"❌ Недостаточно звёзд для вывода! Минимальная сумма: {admin_db['settings']['min_withdraw']}⭐\n"
            f"Текущий баланс: {admin_db['stars_balance']}⭐"
        )
        log_event(message.from_user.id, f"Попытка вывода (недостаточно средств: {admin_db['stars_balance']}⭐)")
        return
    
    await state.set_state(PaymentState.waiting_for_withdraw_amount)
    await message.answer(
        f"💰 Доступно для вывода: {admin_db['stars_balance']}⭐\n"
        f"Минимальная сумма вывода: {admin_db['settings']['min_withdraw']}⭐\n\n"
        "Введите сумму для вывода:"
    )
    log_event(message.from_user.id, "Запрос на вывод средств")

@dp.message(PaymentState.waiting_for_withdraw_amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
        
        if amount > admin_db['stars_balance']:
            await message.answer(f"❌ Недостаточно звёзд на балансе бота для вывода. Доступно: {admin_db['stars_balance']}⭐")
        elif amount < admin_db['settings']['min_withdraw']:
            await message.answer(f"❌ Сумма вывода должна быть не меньше {admin_db['settings']['min_withdraw']}⭐")
        else:
            admin_db['stars_balance'] -= amount
            await message.answer(f"✅ Успешно выведено {amount}⭐. Баланс бота: {admin_db['stars_balance']}⭐")
            log_event(message.from_user.id, f"Выведено {amount}⭐. Баланс бота: {admin_db['stars_balance']}⭐")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число.")
    finally:
        await state.clear()
        save_data()

@dp.message(PaymentState.waiting_for_user_id)
async def process_user_id_for_block(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        data = await state.get_data()
        action = data['action']
        
        if user_id in users_db:
            if action == "block":
                users_db[user_id]['is_blocked'] = True
                await message.answer(f"✅ Пользователь {user_id} заблокирован.")
                log_event(message.from_user.id, f"Заблокирован пользователь {user_id}")
            else:
                users_db[user_id]['is_blocked'] = False
                await message.answer(f"✅ Пользователь {user_id} разблокирован.")
                log_event(message.from_user.id, f"Разблокирован пользователь {user_id}")
        else:
            await message.answer("❌ Пользователь с таким ID не найден.")
        
        save_data()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID пользователя (число).")
    finally:
        await state.clear()

@dp.message(lambda message: message.text == "📊 Логи пользователей")
async def show_user_logs(message: types.Message):
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = f.read()
            if len(logs) > 4096:
                await message.answer("Лог-файл слишком большой для отправки. Он был сохранен локально.")
            else:
                await message.answer(f"Содержимое лог-файла:\n\n```{logs}```")
    except FileNotFoundError:
        await message.answer("❌ Лог-файл не найден.")

@dp.message(lambda message: message.text == "🔍 Проверить выигрышный код")
async def check_win_code(message: types.Message, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_win_code)
    await message.answer("Введите выигрышный код для проверки:")

@dp.message(PaymentState.waiting_for_win_code)
async def process_check_win_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if code in win_codes_db:
        win_info = win_codes_db[code]
        status = "Использован" if win_info['used'] else "Не использован"
        await message.answer(
            f"✅ Код найден!\n"
            f"ID пользователя: {win_info['user_id']}\n"
            f"Тип игры: {win_info['game_type']}\n"
            f"Дата выигрыша: {win_info['timestamp']}\n"
            f"Статус: {status}"
        )
    else:
        await message.answer("❌ Код не найден.")
    await state.clear()

@dp.message(lambda message: message.text == "💾 Сохранить данные")
async def manual_save_data(message: types.Message):
    save_data()
    await message.answer("✅ Данные сохранены.")

async def main():
    load_data()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
