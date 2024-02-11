import logging, re, asyncio
from datetime import datetime
from aiogram.utils import exceptions
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher

from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import sqlite3

API_TOKEN = '6552137964:AAGjuuGiXXVt1CTubNU4xGRfHDHjtQIu8_0'

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
        phone_number TEXT,
        bank TEXT
    )
''')
conn.commit()


class RegisterStates(StatesGroup):
    name = State()
    birth_date = State()
    bank = State()
    phone_number = State()


banks_markup = ReplyKeyboardMarkup(resize_keyboard=True).add('Cбербанк', 'Тинькофф-банк', 'Альфа-Банк')
main_markup = ReplyKeyboardMarkup(resize_keyboard=True).add('Зарегистрироваться')
phone_markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('Поделиться номером', request_contact=True))


def insert_to_table(data, user_id):
    existing_user = cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    if existing_user:
        cursor.execute('''
            UPDATE users 
            SET username=?, birth_date=?, phone_number=?, bank=?
            WHERE user_id=?
        ''', (data['name'], data['birth_date'], data['phone_number'], data['bank'], user_id))
    else:
        cursor.execute('''
            INSERT INTO users (user_id, username, birth_date, phone_number, bank)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, data['name'], data['birth_date'], data['phone_number'], data['bank']))

    conn.commit()


def get_users_with_birthday():
    # Устанавливаем соединение с базой данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%d-%m")
    cursor.execute("SELECT * FROM users WHERE birth_date = ?", (today,))
    users = cursor.fetchall()
    conn.close()
    return users


def get_all_users():
    conn = sqlite3.connect('users.db')  # Замените 'your_database.db' на имя вашей базы данных
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return users


async def send_message_to_all_users(message_text):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user_id in users:
        user_id = user_id[0]  # user_id находится в кортеже, извлекаем его
        try:
            await bot.send_message(chat_id=user_id, text=message_text)
            print(f"Сообщение отправлено пользователю с ID {user_id}")
        except exceptions.TelegramAPIError as e:
            print(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот для регистрации дней рождения. Нажми 'Зарегистрироваться', чтобы начать.",
                         reply_markup=main_markup)


@dp.message_handler(lambda message: message.text == 'Зарегистрироваться', state='*')
async def process_register(message: types.Message):
    await message.answer("Как тебя зовут?")
    await RegisterStates.name.set()


@dp.message_handler(state=RegisterStates.name)
async def process_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введи свое имя.")
        return

    if len(message.text) < 15 and len(message.text) > 0:
        name = message.text
        await state.update_data(name=name)
        await message.answer(f"Приятно познакомиться, {name}! Введи свою дату рождения в формате ДД.ММ.ГГГГ")
        await RegisterStates.birth_date.set()
    else:
        await message.answer("Пожалуйста, введи корректное имя.")
        return


@dp.message_handler(state=RegisterStates.birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    banks_markup = ReplyKeyboardMarkup(resize_keyboard=True).add('Cбербанк', 'Тинькофф-банк').add('Альфа-Банк', 'Райффайзенбанк')
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используй формат ДД.ММ.ГГГГ.")
        return
    birth_date = message.text
    await state.update_data(birth_date=birth_date)
    await message.answer("Теперь укажи банк, которым вы пользуетесь", reply_markup=banks_markup)
    await RegisterStates.bank.set()


@dp.message_handler(state=RegisterStates.bank)
async def process_name_bank(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, укажи банк.")
        return

    bank = message.text
    await state.update_data(bank=bank)
    await message.answer("Теперь укажи свой номер телефона", reply_markup=phone_markup)
    await RegisterStates.phone_number.set()


@dp.message_handler(state=RegisterStates.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    if message.content_type == types.ContentTypes.CONTACT:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text
        if not re.match("^\d{10,15}$", phone_number):
            await message.answer("Некорректный формат номера телефона. Пожалуйста, используй формат +1234567890.")
            return


    await state.update_data(phone_number=phone_number)
    data = await state.get_data()
    insert_to_table(data, message.from_user.id)
    await state.finish()

    await message.answer("Спасибо за регистрацию! Теперь ты будешь получать уведомления о днях рождения.")
    await message.answer("Если хочешь изменить свои данные, просто нажми /start снова.", reply_markup=main_markup)


@dp.message_handler(content_types=types.ContentTypes.CONTACT, state=RegisterStates.phone_number)
async def handle_contact(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)
    data = await state.get_data()
    insert_to_table(data, message.from_user.id)
    await state.finish()

    await message.answer("Спасибо за регистрацию! Теперь ты будешь получать уведомления о днях рождения.")
    await message.answer("Если хочешь изменить свои данные, просто нажми /start снова.", reply_markup=main_markup)


@dp.message_handler(commands=['gg'])
async def cmd_start(message: types.Message):
    await send_birthday_messages()


async def send_birthday_messages():
    # Получаем текущую дату
    today = datetime.now().strftime("%d.%m")
    print('today', today)
    # Получаем из базы данных всех пользователей
    all_users = get_all_users()
    print('au', all_users)
    # Фильтруем пользователей, у которых сегодня день рождения
    users_with_birthday = [user for user in all_users if user[2][:5] == today]
    print('uwb', users_with_birthday)


    for user in users_with_birthday:

        user_id = user[0]  # Первый элемент кортежа - ID пользователя
        user_name = user[1]  # Второй элемент кортежа - Имя пользователя
        user_phone_number = user[3]  # Третий элемент кортежа - Номер телефона
        user_bank = user[4]  # Четвертый элемент кортежа - Название банка

        message_text = f"Сегодня у {user_name} день рождения! 🎉\n" \
                       f"Поздравляем! Желаем счастья, здоровья и удачи во всех начинаниях! 🎂\n" \
                       f"Телефон: {user_phone_number}\n" \
                       f"Банк: {user_bank}"

        try:
            await send_message_to_all_users(message_text)
        except exceptions.BotBlocked:
            print(f"Пользователь {user_id} заблокировал бота")
        except exceptions.ChatNotFound:
            print(f"Чат с пользователем {user_id} не найден")
        except exceptions.RetryAfter as e:
            print(f"Получен RetryAfter {e.timeout} секунд для пользователя {user_id}")
            await asyncio.sleep(e.timeout)
            return await send_birthday_messages()
        except exceptions.UserDeactivated:
            print(f"Пользователь {user_id} деактивировал свой аккаунт")
        except exceptions.MessageIsTooLong:
            print(f"Сообщение для пользователя {user_id} слишком длинное")


async def scheduler():
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            await send_birthday_messages()
        await asyncio.sleep(60)


async def on_startup(_):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    from aiogram import executor

    logging.basicConfig(level=logging.INFO)

    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
