import os
import sqlite3
import asyncio
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

# Очистка таблицы перед добавлением данных
print("Очистка таблицы characters...")
try:
    cursor.execute("DELETE FROM characters")
    print("Таблица очищена.")
except Exception as e:
    print(f"Ошибка при очистке таблицы: {e}")

# Добавление начальных данных
print("Добавление данных в таблицу...")
try:
    cursor.execute("INSERT INTO characters VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("Человек-паук Нуар", "Marvel", "Marvel Noir", "Герой",
                    "Мрачный Питер Паркер из 1930-х, мститель с револьвером.",
                    "https://t.me/KomicsHub/3", "https://t.me/KomicsHub/4"))
    cursor.execute("INSERT INTO characters VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("Спаун", "Image", "Spawn Universe", "Антигерой",
                    "Эл Симмонс, наемник, ставший мстителем ада с цепями.",
                    "https://t.me/komikshub/post2", "https://example.com/art2.jpg"))
    conn.commit()
    print("Данные успешно добавлены.")
except Exception as e:
    print(f"Ошибка при добавления данных: {e}")

# Проверка содержимого базы данных
print("Проверка содержимого базы данных...")
try:
    cursor.execute("SELECT * FROM characters")
    results = cursor.fetchall()
    print(f"Данные в базе: {results}")
    if not results:
        print("ВНИМАНИЕ: База данных пуста!")
except Exception as e:
    print(f"Ошибка при проверке содержимого базы данных: {e}")

# Создание главного меню с кнопками
menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Поиск", callback_data="search")],
    [InlineKeyboardButton(text="🎲 Случайный", callback_data="random")],
    [InlineKeyboardButton(text="⚔️ Кроссовер", callback_data="crossover")]
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

# Команда /addcharacter (только для администратора)
@dp.message(Command(commands=["addcharacter"]))
async def add_character_start(message: types.Message, state: FSMContext):
    admin_id = 376742720  # Твой Telegram ID
    if message.from_user.id != admin_id:
        print(f"Пользователь {message.from_user.id} попытался использовать /addcharacter, но доступ запрещён")
        return  # Игнорируем команду, если пользователь не администратор

    print(f"Получена команда /addcharacter от администратора {message.from_user.id}")
    await state.clear()  # Сбрасываем состояние
    await state.set_state(AddCharacterStates.waiting_for_name)
    await message.reply("Введите имя персонажа (например, Человек-паук Нуар):")

# Обработка имени персонажа
@dp.message(AddCharacterStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AddCharacterStates.waiting_for_publisher)
    await message.reply("Введите издателя (например, Marvel):")

# Обработка издателя
@dp.message(AddCharacterStates.waiting_for_publisher)
async def process_publisher(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    publisher = message.text.strip()
    await state.update_data(publisher=publisher)
    await state.set_state(AddCharacterStates.waiting_for_universe)
    await message.reply("Введите вселенную (например, Marvel Noir):")

# Обработка вселенной
@dp.message(AddCharacterStates.waiting_for_universe)
async def process_universe(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    universe = message.text.strip()
    await state.update_data(universe=universe)
    await state.set_state(AddCharacterStates.waiting_for_type)
    await message.reply("Введите тип персонажа (например, Герой, Антигерой, Злодей):")

# Обработка типа
@dp.message(AddCharacterStates.waiting_for_type)
async def process_type(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    type_ = message.text.strip()
    await state.update_data(type=type_)
    await state.set_state(AddCharacterStates.waiting_for_description)
    await message.reply("Введите описание персонажа (например, Мрачный Питер Паркер из 1930-х...):")

# Обработка описания
@dp.message(AddCharacterStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    description = message.text.strip()
    await state.update_data(description=description)
    await state.set_state(AddCharacterStates.waiting_for_post_link)
    await message.reply("Введите ссылку на пост (например, https://t.me/KomicsHub/3):")

# Обработка ссылки на пост
@dp.message(AddCharacterStates.waiting_for_post_link)
async def process_post_link(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    post_link = message.text.strip()
    await state.update_data(post_link=post_link)
    await state.set_state(AddCharacterStates.waiting_for_art_link)
    await message.reply("Введите ссылку на арт (например, https://example.com/art.jpg):")

# Обработка ссылки на арт и сохранение персонажа
@dp.message(AddCharacterStates.waiting_for_art_link)
async def process_art_link(message: types.Message, state: FSMContext):
    admin_id = 376742720
    if message.from_user.id != admin_id:
        return

    art_link = message.text.strip()
    data = await state.get_data()
    name = data["name"]
    publisher = data["publisher"]
    universe = data["universe"]
    type_ = data["type"]
    description = data["description"]
    post_link = data["post_link"]

    # Сохраняем персонажа в базу данных
    try:
        cursor.execute("INSERT INTO characters VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (name, publisher, universe, type_, description, post_link, art_link))
        conn.commit()
        await message.reply(f"Персонаж {name} успешно добавлен! 🎉")
        print(f"Администратор {message.from_user.id} добавил персонажа: {name}")
    except Exception as e:
        await message.reply(f"Ошибка при добавлении персонажа: {e}")
        print(f"Ошибка при добавлении персонажа администратором {message.from_user.id}: {e}")

    await state.clear()

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
    elif data == "crossover":
        print(f"Выполняется запрос на кроссовер...")
        cursor.execute("SELECT * FROM characters ORDER BY RANDOM() LIMIT 2")
        fighters = cursor.fetchall()
        if len(fighters) == 2:
            fighter1, fighter2 = fighters[0], fighters[1]
            buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=fighter1[0], callback_data=f"vote_{fighter1[0]}"),
                 InlineKeyboardButton(text=fighter2[0], callback_data=f"vote_{fighter2[0]}")]
            ])
            await callback_query.message.reply(
                f"⚔️ Кроссовер: {fighter1[0]} vs. {fighter2[0]} — кто победит? 😈",
                reply_markup=buttons
            )
            print(f"Кроссовер создан: {fighter1[0]} vs. {fighter2[0]}")
        else:
            await callback_query.message.reply("Недостаточно персонажей для кроссовера. Добавьте больше персонажей! 😔")
            print("Кроссовер не создан: недостаточно персонажей")

# Обработка голосования в кроссовере
@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback_query: types.CallbackQuery):
    winner = callback_query.data.split("_")[1]
    print(f"Пользователь {callback_query.from_user.id} проголосовал за {winner}")
    await callback_query.message.reply(f"Ты выбрал {winner}! Спасибо за голос! 🏆")
    await callback_query.answer()

# Обработка текстовых сообщений (поиск в личных чатах)
@dp.message(SearchStates.waiting_for_query)
async def handle_search_query(message: types.Message, state: FSMContext):
    query = message.text.lower().strip().replace("-", " ").replace("  ", " ")  # Убираем лишние пробелы и дефисы
    query_parts = query.split()  # Разбиваем запрос на слова
    print(f"Запрос пользователя {message.from_user.id}: {query} (разбит на части: {query_parts})")

    # Получаем все записи из базы данных
    cursor.execute("SELECT * FROM characters")
    all_characters = cursor.fetchall()
    results = []

    # Нечёткий поиск: проверяем каждую запись
    for character in all_characters:
        name, publisher, universe, type_, desc, link, art = character
        combined_text = f"{name} {publisher} {universe} {type_}".lower()
        max_score = 0
        for part in query_parts:
            score = fuzz.partial_ratio(part, combined_text)
            if score > max_score:
                max_score = score
        if max_score >= 70:
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

    # Не сбрасываем состояние, чтобы пользователь мог продолжить поиск
    print(f"Пользователь {message.from_user.id} остаётся в режиме поиска")

# Обработка выбора персонажа из списка
@dp.callback_query(lambda c: c.data.startswith("select_"))
async def handle_selection(callback_query: types.CallbackQuery):
    selected_name = callback_query.data.split("_")[1]
    print(f"Пользователь {callback_query.from_user.id} выбрал персонажа: {selected_name}")
    cursor.execute("SELECT * FROM characters WHERE name = ?", (selected_name,))
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
        print(f"Пользователь {callback_query.from_user.id}: информация о персонаже {name} отправлена")
    await callback_query.answer()

# Обработка комментариев в группе (ответов на пересланные посты)
@dp.message(lambda message: message.reply_to_message is not None and message.chat.type in ["group", "supergroup"])
async def handle_comment(message: types.Message, state: FSMContext):
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        query = message.text.lower().strip().replace("-", " ").replace("  ", " ")
        query_parts = query.split()
        print(f"Комментарий пользователя {message.from_user.id} в группе: {query} (разбит на части: {query_parts})")

        cursor.execute("SELECT * FROM characters")
        all_characters = cursor.fetchall()
        results = []

        for character in all_characters:
            name, publisher, universe, type_, desc, link, art = character
            combined_text = f"{name} {publisher} {universe} {type_}".lower()
            max_score = 0
            for part in query_parts:
                score = fuzz.partial_ratio(part, combined_text)
                if score > max_score:
                    max_score = score
            if max_score >= 70:
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
                    reply_markup=buttons, reply_to_message_id=message.message_id
                )
                print(f"Пользователь {message.from_user.id}: найден 1 персонаж: {name}")
            else:
                buttons = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{result[0]} ({result[1]})", callback_data=f"select_{result[0]}")] for result in results
                ])
                await message.reply("Найдено несколько персонажей. Выбери одного:",
                                   reply_markup=buttons, reply_to_message_id=message.message_id)
                print(f"Пользователь {message.from_user.id}: найдено несколько персонажей: {[result[0] for result in results]}")
        else:
            await message.reply("Информации о таком персонаже нет. 😔",
                               reply_to_message_id=message.message_id)
            print(f"Пользователь {message.from_user.id}: персонажи не найдены для запроса '{query}'")
    else:
        print(f"Сообщение пользователя {message.from_user.id} в группе не является комментарием: {message.text}")

# Обработка текстовых сообщений, когда пользователь не в режиме поиска
@dp.message()
async def handle_text(message: types.Message, state: FSMContext):
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