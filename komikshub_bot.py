import os
import sqlite3
import asyncio
import requests  # Добавляем библиотеку для скачивания файла
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fuzzywuzzy import fuzz
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Определяем состояния для FSM
class SearchStates(StatesGroup):
    waiting_for_query = State()

class AddCharacterStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_publisher = State()
    waiting_for_universe = State()
    waiting_for_type = State()
    waiting_for_description = State()
    waiting_for_post_link = State()
    waiting_for_art_link = State()

# Инициализация aiogram
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Публичная ссылка на файл базы данных в Mail.ru Cloud
DATABASE_URL = "https://cloud.mail.ru/public/XXXX/YYYY"  # Замени на свою публичную ссылку

# Скачивание файла базы данных из облака
print("Скачивание базы данных из облака...")
try:
    response = requests.get(DATABASE_URL)
    with open('comics_characters.db', 'wb') as f:
        f.write(response.content)
    print("База данных успешно скачана.")
except Exception as e:
    print(f"Ошибка при скачивании базы данных: {e}")

# Подключение к базе данных SQLite с поддержкой UTF-8
print("Подключение к базе данных...")
try:
    conn = sqlite3.connect('comics_characters.db')
    cursor = conn.cursor()
    conn.execute('PRAGMA encoding = "UTF-8";')
    print("База данных успешно подключена.")
except Exception as e:
    print(f"Ошибка подключения к базе данных: {e}")

# Создание таблицы в базе данных
print("Создание таблицы characters...")
try:
    cursor.execute('''CREATE TABLE IF NOT EXISTS characters
                   (name TEXT, publisher TEXT, universe TEXT, type TEXT, description TEXT, post_link TEXT, art_link TEXT)''')
    print("Таблица characters создана или уже существует.")
except Exception as e:
    print(f"Ошибка при создании таблицы: {e}")

# Функция для проверки и заполнения базы данных
def ensure_database_populated():
    print("Проверка содержимого базы данных...")
    try:
        cursor.execute("SELECT * FROM characters")
        results = cursor.fetchall()
        print(f"Данные в базе: {results}")
        if not results:
            print("ВНИМАНИЕ: База данных пуста! Добавляем начальные данные...")
            cursor.execute("INSERT INTO characters VALUES (?, ?, ?, ?, ?, ?, ?)",
                           ("Человек-паук Нуар", "Marvel", "Marvel Noir", "Герой",
                            "Мрачный Питер Паркер из 1930-х, мститель с револьвером.",
                            "https://t.me/KomicsHub/3", "https://t.me/KomicsHub/4"))
            cursor.execute("INSERT INTO characters VALUES (?, ?, ?, ?, ?, ?, ?)",
                           ("Спаун", "Image", "Spawn Universe", "Антигерой",
                            "Эл Симмонс, наемник, ставший мстителем ада с цепями.",
                            "https://t.me/komikshub/post2", "https://example.com/art2.jpg"))
            conn.commit()
            print("Начальные данные успешно добавлены.")
    except Exception as e:
        print(f"Ошибка при проверке содержимого базы данных: {e}")

# Вызываем функцию при запуске
ensure_database_populated()

# Создание главного меню с кнопками
menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Поиск", callback_data="search")],
    [InlineKeyboardButton(text="🎲 Случайный", callback_data="random")]
])

# Команда /start
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    print(f"Получена команда /start от пользователя {message.from_user.id}")
    await state.clear()  # Сбрасываем состояние, если оно есть
    await message.reply("🦸 Привет! Я бот канала КомиксХаб! Помогу найти героев комиксов. Выбери действие:", reply_markup=menu)

# Команда /cancel для выхода из режима поиска
@dp.message(Command(commands=["cancel"]))
async def cancel(message: types.Message, state: FSMContext):
    print(f"Получена команда /cancel от пользователя {message.from_user.id}")
    await state.clear()
    await message.reply("Поиск завершён. Используй /start, чтобы начать заново. 😊")

# Обработка кнопок главного меню
@dp.callback_query()
async def handle_buttons(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    print(f"Пользователь {callback_query.from_user.id} нажал кнопку: {data}")
    await callback_query.answer()

    if data == "search":
        await callback_query.message.reply("Введи запрос (например, паук, нуар, Marvel):")
        await state.set_state(SearchStates.waiting_for_query)
        print(f"Пользователь {callback_query.from_user.id} перешёл в режим поиска")
    elif data == "random":
        print(f"Выполняется запрос на случайного персонажа...")
        ensure_database_populated()  # Перезаполняем базу перед запросом
        cursor.execute("SELECT * FROM characters ORDER BY RANDOM() LIMIT 1")
        result = cursor.fetchone()
        if result:
            name, publisher, universe, type_, desc, link, art = result
            buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Арт", url=art)]
            ])
            await callback_query.message.reply(
                f"🦸 {name}\n📚 Издатель: {publisher}\n🌌 Вселенная: {universe}\n🦸 Тип: {type_}\n📖 {desc}\n📜 Пост: {link}",
                reply_markup=buttons
            )
            print(f"Случайный персонаж найден: {name}")
        else:
            await callback_query.message.reply("Персонажи не найдены. База данных пуста. 😔")
            print("Случайный персонаж не найден: база данных пуста")

# Обработка текстовых сообщений (поиск в личных чатах)
@dp.message(SearchStates.waiting_for_query)
async def handle_search_query(message: types.Message, state: FSMContext):
    print(f"Пользователь {message.from_user.id} отправил запрос в состоянии waiting_for_query")
    query = message.text.lower().strip().replace("-", " ").replace("  ", " ")  # Убираем лишние пробелы и дефисы
    query_parts = query.split()  # Разбиваем запрос на слова
    print(f"Запрос пользователя {message.from_user.id}: {query} (разбит на части: {query_parts})")

    # Перезаполняем базу перед запросом
    ensure_database_populated()

    # Получаем все записи из базы данных
    cursor.execute("SELECT * FROM characters")
    all_characters = cursor.fetchall()
    print(f"Все персонажи в базе: {all_characters}")
    results = []

    # Нечёткий поиск: проверяем каждую запись
    for character in all_characters:
        name, publisher, universe, type_, desc, link, art = character
        combined_text = f"{name} {publisher} {universe} {type_}".lower()
        max_score = 0
        for part in query_parts:
            score = fuzz.partial_ratio(part, combined_text)
            print(f"Сравниваем '{part}' с '{combined_text}': score={score}")
            if score > max_score:
                max_score = score
        if max_score >= 50:  # Порог уже снижен до 50
            results.append(character)
            print(f"Персонаж {name} найден с уровнем сходства {max_score}%")

    print(f"Найдено записей: {len(results)}")
    print(f"Результаты: {results}")

    if results:
        if len(results) == 1:
            name, publisher, universe, type_, desc, link, art = results[0]
            buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Арт", url=art)]
            ])
            await message.reply(
                f"🦸 {name}\n📚 Издатель: {publisher}\n🌌 Вселенная: {universe}\n🦸 Тип: {type_}\n📖 {desc}\n📜 Пост: {link}",
                reply_markup=buttons
            )
            print(f"Пользователь {message.from_user.id}: найден 1 персонаж: {name}")
        else:
            buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{result[0]} ({result[1]})", callback_data=f"select_{result[0]}")] for result in results
            ])
            await message.reply("Найдено несколько персонажей. Выбери одного:", reply_markup=buttons)
            print(f"Пользователь {message.from_user.id}: найдено несколько персонажей: {[result[0] for result in results]}")
    else:
        await message.reply("Персонаж не найден! Попробуй другой запрос. 😎")
        print(f"Пользователь {message.from_user.id}: персонажи не найдены для запроса '{query}'")

    # Сбрасываем состояние после обработки
    await state.clear()
    print(f"Пользователь {message.from_user.id}: состояние сброшено, текущее состояние: {await state.get_state()}")

# Обработка выбора персонажа из списка
@dp.callback_query(lambda c: c.data.startswith("select_"))
async def handle_selection(callback_query: types.CallbackQuery):
    selected_name = callback_query.data.split("_", 1)[1]  # Исправляем split, чтобы обработать имена с пробелами
    print(f"Пользователь {callback_query.from_user.id} выбрал персонажа: {selected_name}")
    try:
        # Перезаполняем базу перед запросом
        ensure_database_populated()

        # Проверяем содержимое базы данных перед запросом
        cursor.execute("SELECT * FROM characters")
        all_characters = cursor.fetchall()
        print(f"Все персонажи в базе перед выбором: {all_characters}")

        # Ищем персонажа
        cursor.execute("SELECT * FROM characters WHERE name = ?", (selected_name,))
        result = cursor.fetchone()
        print(f"Результат запроса к базе данных: {result}")
        if result:
            name, publisher, universe, type_, desc, link, art = result
            buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Арт", url=art)]
            ])
            try:
                await callback_query.message.reply(
                    f"🦸 {name}\n📚 Издатель: {publisher}\n🌌 Вселенная: {universe}\n🦸 Тип: {type_}\n📖 {desc}\n📜 Пост: {link}",
                    reply_markup=buttons
                )
                print(f"Пользователь {callback_query.from_user.id}: информация о персонаже {name} отправлена")
            except Exception as send_error:
                print(f"Ошибка при отправке сообщения в Telegram: {send_error}")
                await callback_query.message.reply(f"Не удалось отправить информацию: {send_error}")
        else:
            await callback_query.message.reply("Персонаж не найден в базе данных. 😔")
            print(f"Пользователь {callback_query.from_user.id}: персонаж {selected_name} не найден в базе данных")
    except Exception as db_error:
        print(f"Ошибка при запросе к базе данных: {db_error}")
        await callback_query.message.reply(f"Произошла ошибка при доступе к базе данных: {db_error}")
    await callback_query.answer()

# Обработка текстовых сообщений, когда пользователь не в режиме поиска
@dp.message()
async def handle_text(message: types.Message, state: FSMContext):
    # Игнорируем пустые сообщения или сообщения без текста
    if not message.text:
        print(f"Сообщение пользователя {message.from_user.id} проигнорировано: текст отсутствует")
        return

    print(f"Пользователь {message.from_user.id} ввёл текст: {message.text}")
    # Игнорируем сообщения в группах
    if message.chat.type in ["group", "supergroup"]:
        print(f"Сообщение пользователя {message.from_user.id} в группе проигнорировано: {message.text}")
        return

    print(f"Пользователь {message.from_user.id} ввёл текст вне режима поиска: {message.text}")
    await message.reply("Введи запрос (например, паук, нуар, Marvel):")
    await state.set_state(SearchStates.waiting_for_query)
    print(f"Пользователь {message.from_user.id} перешёл в режим поиска")

# Минимальный HTTP-сервер для health checks Render
async def handle_health(request):
    return web.Response(text="The bot is running fine :)")

# Настройка HTTP-сервера
web_app = web.Application()
web_app.add_routes([web.get('/healthcheck', handle_health)])

# Запуск polling и HTTP-сервера
async def main():
    # Удаляем вебхук перед запуском polling
    print("Удаление существующего вебхука...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("Вебхук удалён, запускаем polling...")

    # Запуск HTTP-сервера для health checks
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.getenv("PORT", 8000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"HTTP server running on http://0.0.0.0:{port}")

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())