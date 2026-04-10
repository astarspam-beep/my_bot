import os
import asyncio
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- ЧАСТИНА ДЛЯ ПІДТРИМКИ ЖИТТЄДІЯЛЬНОСТІ (Щоб Render не вимикав бота) ---
app = Flask('')

@app.route('/')
def home():
    return "Бот працює!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- НАЛАШТУВАННЯ БОТА ---
# Ми беремо токен та ID адміна з налаштувань Render (Environment Variables)
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Стани для анкети
class Form(StatesGroup):
    name = State()
    phone = State()
    idea = State()

# Головне меню (нижні кнопки)
def main_menu():
    buttons = [
        [KeyboardButton(text="Свіжі квіти 🌸"), KeyboardButton(text="Гострі ножі 🔪")],
        [KeyboardButton(text="Чиста вода та повітря 💧"), KeyboardButton(text="Тверезий водій 🚗")],
        [KeyboardButton(text="Стильний бокс 🧦"), KeyboardButton(text="Speak-партнер 🎙️")],
        [KeyboardButton(text="Особистий запит 🎯")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Кнопки під текстом розділу
def order_menu(is_idea=False):
    btn_text = "✅ Описати ідею" if is_idea else "✅ Оформити та забути"
    buttons = [
        [KeyboardButton(text=btn_text)],
        [KeyboardButton(text="⬅️ Повернутися")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Обробка команди /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Ваш час занадто цінний, щоб витрачати його на дрібниці. Оберіть сферу, яку ми візьмемо під свій контроль:",
        reply_markup=main_menu()
    )

# Відображення розділів
@dp.message(F.text.in_([
    "Свіжі квіти 🌸", "Гострі ножі 🔪", "Чиста вода та повітря 💧", 
    "Тверезий водій 🚗", "Стильний бокс 🧦", "Speak-партнер 🎙️", "Особистий запит 🎯"
]))
async def show_section(message: types.Message):
    content = {
        "Свіжі квіти 🌸": "✨ Створіть атмосферу свята... Достатньо один раз налаштувати підписку.\n\nВартість: від 400 грн.",
        "Гострі ножі 🔪": "✨ Вам більше не потрібно боротися з тупими лезами... Вартість: від 300 грн.",
        "Чиста вода та повітря 💧": "✨ Здоров’я та енергія починаються з води... Вартість: від 500 грн.",
        "Тверезий водій 🚗": "✨ Ваш персональний водій буде готовий до виїзду... Вартість: від 800 грн.",
        "Стильний бокс 🧦": "✨ Ваш ідеальний базовий гардероб... Вартість: від 450 грн.",
        "Speak-партнер 🎙️": "✨ Професійний співрозмовник буде на зв'язку... Вартість: від 600 грн.",
        "Особистий запит 🎯": "✨ Якщо у вас є особливе завдання або специфічна рутина... Вартість: Індивідуально."
    }
    text = content.get(message.text, "Оберіть дію:")
    await message.answer(text, reply_markup=order_menu(message.text == "Особистий запит 🎯"))

# Початок оформлення
@dp.message(F.text == "✅ Оформити та забути")
async def start_standard(message: types.Message, state: FSMContext):
    await message.answer("Щоб оформити заявку, напишіть, будь ласка, ваше Прізвище та Ім'я.")
    await state.set_state(Form.name)

@dp.message(F.text == "✅ Описати ідею")
async def start_idea(message: types.Message, state: FSMContext):
    await message.answer("Опишіть коротко, яку підписку ви хотіли б створити?")
    await state.set_state(Form.idea)

# Обробка ідеї
@dp.message(Form.idea)
async def process_idea(message: types.Message, state: FSMContext):
    await state.update_data(user_idea=message.text)
    await message.answer("Зрозумів! Тепер напишіть ваше Прізвище та Ім'я.")
    await state.set_state(Form.name)

# Обробка ПІБ
@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(user_name=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Надіслати номер телефону", request_contact=True)]], resize_keyboard=True)
    await message.answer("Дякую! Тепер натисніть кнопку нижче для зв'язку.", reply_markup=kb)
    await state.set_state(Form.phone)

# Обробка телефону та фінал
@dp.message(Form.phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number
    
    # Повідомлення адміну
    await bot.send_message(ADMIN_ID, f"🔔 НОВА ЗАЯВКА!\nКлієнт: {data['user_name']}\nТел: {phone}\nІдея: {data.get('user_idea', '-')}")
    
    await message.answer("Дякуємо! Вашу заявку прийнято. Менеджер зв'яжеться з вами. Гарного дня!", reply_markup=main_menu())
    await state.clear()

# Кнопка Повернутися
@dp.message(F.text == "⬅️ Повернутися")
async def back(message: types.Message, state: FSMContext):
    await cmd_start(message, state)

async def main():
    keep_alive() # Запускаємо міні-сайт для стабільної роботи
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
