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
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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
                # Преобразование ключей из строк в int (так как JSON ключи словаря всегда строки)
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

# Обработчики команд
@dp.message(Command("start", "help"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
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
    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    await message.answer("Выберите вариант игры:", reply_markup=get_game_keyboard())

@dp.message(lambda message: message.text == "💰 Пополнить баланс")
async def add_balance(message: types.Message):
    user_id = message.from_user.id
    if users_db.get(user_id, {}).get('is_blocked', False):
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    await message.answer("Выберите сумму пополнения:", reply_markup=get_payment_keyboard())

@dp.message(lambda message: message.text == "📊 Статистика")
async def show_stats(message: types.Message):
    user_id = message.from_user.id
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

# Обработчики игры с новой системой призов
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
    
    # Отправляем мяч как отдельное сообщение
    await message.answer("🏀")
    
    user_data['balance'] -= cost
    admin_db['stars_balance'] += cost
    user_data['games_played'] += 1
    
    log_event(user_id, f"Списано {cost}⭐ за игру в 1 мяч. Баланс: {user_data['balance']}⭐")
    
    # Имитация броска с задержкой
    await asyncio.sleep(2)
    
    # Новая система призов: 1/1 - выиграл
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
    
    # Бросаем 2 мяча по очереди
    hits = 0
    
    for i in range(2):
        # Отправляем мяч как отдельное сообщение
        await message.answer("🏀")
        await asyncio.sleep(1.5)  # Задержка между бросками
        
        # Определяем попадание и отправляем результат
        if random.random() < admin_db['settings']['ball2_chance']:
            hits += 1
            await message.answer("✅ Попал!")
        else:
            await message.answer("❌ Промах!")
        await asyncio.sleep(0.5)
    
    # Новая система призов: 2/2 - выиграл, 1/2 - проиграл, 0/2 - проиграл
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
    
    # Бросаем 3 мяча по очереди
    hits = 0
    
    for i in range(3):
        # Отправляем мяч как отдельное сообщение
        await message.answer("🏀")
        await asyncio.sleep(1.5)  # Задержка между бросками
        
        # Определяем попадание и отправляем результат
        if random.random() < admin_db['settings']['ball3_chance']:
            hits += 1
            await message.answer("✅ Попал!")
        else:
            await message.answer("❌ Промах!")
        await asyncio.sleep(0.5)
    
    # Новая система призов: 3/3 - выиграл, 2/3 - проиграл, 1/3 - проиграл, 0/3 - проиграл
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

# Обработчики пополнения баланса
@dp.message(lambda message: message.text in ["5⭐", "10⭐", "100⭐"])
async def process_payment(message: types.Message):
    amount = int(message.text.replace("⭐", ""))
    user_id = message.from_user.id
    
    # Создаем инлайн кнопку для оплаты
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
        
        # Создаем инлайн кнопку для оплаты
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

# Обработчики админ-панели
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
        min_withdraw = admin_db['settings']['min_withdraw']
        
        if amount < min_withdraw:
            await message.answer(f"❌ Минимальная сумма вывода: {min_withdraw}⭐")
            log_event(message.from_user.id, f"Попытка вывода {amount}⭐ (меньше минимума)")
            return
        
        if amount > admin_db['stars_balance']:
            await message.answer(f"❌ Недостаточно звёзд для вывода! Доступно: {admin_db['stars_balance']}⭐")
            log_event(message.from_user.id, f"Попытка вывода {amount}⭐ (недостаточно средств)")
            return
        
        admin_db['stars_balance'] -= amount
        await message.answer(
            f"✅ Запрос на вывод {amount}⭐ успешно отправлен!\n"
            f"Остаток на балансе: {admin_db['stars_balance']}⭐",
            reply_markup=get_admin_keyboard()
        )
        log_event(message.from_user.id, f"Вывод {amount}⭐. Остаток: {admin_db['stars_balance']}⭐")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите целое число")
        return
    
    await state.clear()
    save_data()

@dp.message(lambda message: message.text == "📊 Логи пользователей")
async def show_user_logs(message: types.Message):
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        if len(logs) > 4000:  # Ограничение Telegram на длину сообщения
            logs = logs[-4000:]  # Берем последние 4000 символов
        
        await message.answer(f"📝 Последние события:\n\n{logs}")
        log_event(message.from_user.id, "Просмотр логов")
    except Exception as e:
        await message.answer("❌ Ошибка при чтении логов")
        log_event(message.from_user.id, f"Ошибка просмотра логов: {str(e)}")

@dp.message(lambda message: message.text == "🔍 Проверить выигрышный код")
async def check_win_code(message: types.Message, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_win_code)
    await message.answer("Введите выигрышный код для проверки:")

@dp.message(PaymentState.waiting_for_win_code)
async def process_win_code_check(message: types.Message, state: FSMContext):
    win_code = message.text.upper().strip()
    
    if win_code in win_codes_db:
        code_info = win_codes_db[win_code]
        user_id = code_info['user_id']
        user_info = users_db.get(user_id, {})
        
        response = (
            f"🔍 Информация о коде {win_code}:\n\n"
            f"🆔 ID пользователя: {user_id}\n"
            f"👤 Имя пользователя: {user_info.get('username', 'не указано')}\n"
            f"🎮 Тип игры: {code_info['game_type']}\n"
            f"📅 Дата выигрыша: {code_info['timestamp']}\n"
            f"💰 Баланс пользователя: {user_info.get('balance', 0)}⭐\n"
            f"🎮 Игр сыграно: {user_info.get('games_played', 0)}\n"
            f"🏆 Игр выиграно: {user_info.get('games_won', 0)}\n"
            f"🔑 Всего кодов у пользователя: {len(user_info.get('win_codes', []))}\n"
            f"✅ Статус кода: {'использован' if code_info['used'] else 'активен'}"
        )
        
        await message.answer(response, reply_markup=get_admin_keyboard())
        log_event(message.from_user.id, f"Проверка кода {win_code} для пользователя {user_id}")
    else:
        await message.answer("❌ Код не найден в базе данных.", reply_markup=get_admin_keyboard())
        log_event(message.from_user.id, f"Попытка проверки несуществующего кода: {win_code}")
    
    await state.clear()

@dp.message(lambda message: message.text == "💾 Сохранить данные")
async def save_data_command(message: types.Message):
    save_data()
    await message.answer("✅ Данные успешно сохранены!")
    log_event(message.from_user.id, "Ручное сохранение данных")

# Обработчик пре-чекаута (для реальных платежей)
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработчик успешной оплаты
@dp.message(lambda message: message.successful_payment is not None)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    amount = message.successful_payment.total_amount // 100  # Сумма в звездах
    
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': 0, 
            'games_played': 0, 
            'games_won': 0,
            'is_blocked': False,
            'win_codes': []
        }
    
    users_db[user_id]['balance'] += amount
    await message.answer(
        f"✅ Ваш баланс пополнен на {amount}⭐\n"
        f"Текущий баланс: {users_db[user_id]['balance']}⭐"
    )
    log_event(user_id, f"Пополнение баланса на {amount}⭐. Новый баланс: {users_db[user_id]['balance']}⭐")
    save_data()

async def main():
    # Загрузка данных при старте
    load_data()
    log_event("SYSTEM", "Бот запущен")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())