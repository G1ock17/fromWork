import logging
import asyncio
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher


from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import sqlite3

API_TOKEN = '5904661871:AAEXgH0810Nr_9h46RpgKddM52ADq5JoBZA'

# Инициализация бота с использованием MemoryStorage
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных SQLite
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        birth_date TEXT,
        phone_number TEXT
    )
''')
conn.commit()

class RegisterStates(StatesGroup):
    name = State()
    birth_date = State()
    phone_number = State()

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    # Показываем клавиатуру с запросом на регистрацию
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Зарегистрироваться'))
    await message.answer("Привет! Я бот для регистрации дней рождения. Нажми 'Зарегистрироваться', чтобы начать.",
                         reply_markup=markup)


# Обработчик кнопки "Зарегистрироваться"
@dp.message_handler(lambda message: message.text == 'Зарегистрироваться', state='*')
async def process_register(message: types.Message):
    # Спрашиваем у пользователя имя
    await message.answer("Как тебя зовут?")
    await RegisterStates.name.set()


# Обработчик имени пользователя
@dp.message_handler(state=RegisterStates.name)
async def process_name(message: types.Message, state: FSMContext):
    # Сохраняем имя и спрашиваем дату рождения
    name = message.text
    await state.update_data(name=name)
    await message.answer(f"Приятно познакомиться, {name}! Введи свою дату рождения в формате ДД.ММ.ГГГГ")
    await RegisterStates.birth_date.set()


# Обработчик даты рождения
@dp.message_handler(state=RegisterStates.birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    # Сохраняем дату рождения и спрашиваем номер телефона
    birth_date = message.text
    await state.update_data(birth_date=birth_date)
    await message.answer("Теперь укажи свой номер телефона")
    await RegisterStates.phone_number.set()


# Обработчик номера телефона
@dp.message_handler(state=RegisterStates.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    # Сохраняем номер телефона и завершаем регистрацию
    phone_number = message.text
    await state.update_data(phone_number=phone_number)

    # Получаем данные из контекста
    data = await state.get_data()

    # Сохраняем пользователя в базу данных
    cursor.execute('''
        INSERT INTO users (user_id, username, birth_date, phone_number)
        VALUES (?, ?, ?, ?)
    ''', (message.from_user.id, data['name'], data['birth_date'], data['phone_number']))
    conn.commit()

    # Завершаем регистрацию
    await state.finish()

    await message.answer("Спасибо за регистрацию! Теперь ты будешь получать уведомления о днях рождения.")
    await message.answer("Если хочешь изменить свои данные, просто нажми /start снова.")


# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    from aiogram.contrib.middlewares.logging import LoggingMiddleware

    logging.basicConfig(level=logging.INFO)

    executor.start_polling(dp, skip_updates=True)
