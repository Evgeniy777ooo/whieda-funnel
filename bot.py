import asyncio
import json
import os
from datetime import datetime

import gspread
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from oauth2client.service_account import ServiceAccountCredentials

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_БОТА")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://твой-username.github.io/whieda-funnel/")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# ==================== GOOGLE SHEETS ====================
GOOGLE_SHEET_NAME = "Whieda Leads"

def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON", "{}"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    except gspread.SpreadsheetNotFound:
        sheet = client.create(GOOGLE_SHEET_NAME).sheet1
        headers = ['Telegram ID', 'Имя', 'Username', 'Язык', 'Начало', 'Завершение', 'Пройдено шагов', 'Статус', 'Последний шаг', 'Последняя активность']
        sheet.insert_row(headers, 1)
    return sheet

def save_lead_to_sheet(data: dict):
    try:
        sheet = get_google_sheet()
        telegram_id = str(data.get('telegram_id', 'unknown'))
        try:
            cell = sheet.find(telegram_id)
            row = cell.row
        except gspread.CellNotFound:
            row = len(sheet.get_all_values()) + 1
        row_data = [telegram_id, data.get('first_name', ''), data.get('username', ''), data.get('language', ''), data.get('start_time', ''), data.get('finish_time', ''), len(data.get('completed_steps', [])), 'Завершено ✅' if data.get('completed') else 'В процессе 🔄', data.get('current_step', 1), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        for i, value in enumerate(row_data, 1):
            sheet.update_cell(row, i, value)
        return True
    except Exception as e:
        print(f"❌ Ошибка Google Sheets: {e}")
        return False

# ==================== БОТ ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    basic_data = {'telegram_id': str(user.id), 'first_name': user.first_name, 'username': user.username or 'нет', 'language': user.language_code or 'ru', 'start_time': datetime.now().isoformat(), 'current_step': 0, 'completed_steps': [], 'completed': False, 'finish_time': None}
    save_lead_to_sheet(basic_data)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Открыть воронку Whieda", web_app=WebAppInfo(url=MINI_APP_URL))]])
    await message.answer("👋 <b>Добро пожаловать в Whieda!</b>\n\nПройдите короткую воронку из 4 шагов:\n🎥 Видео о компании\n📊 Презентация продукта\n💬 Чат сообщества\n🌍 Сайты компании\n\n<i>Нажмите кнопку ниже, чтобы начать 👇</i>", reply_markup=keyboard, parse_mode="HTML")

@dp.message()
async def handle_webapp_data(message: types.Message):
    if message.web_app_data:
        try:
            data = json.loads(message.web_app_data.data)
            save_lead_to_sheet(data)
            if data.get('action') == 'completed' and ADMIN_CHAT_ID:
                admin_text = f"🎯 <b>Лид завершил воронку!</b>\n\n👤 {data.get('first_name')}\n📱 @{data.get('username')}\n🆔 {data.get('telegram_id')}\n📊 Пройдено шагов: {len(data.get('completed_steps', []))}\n🕐 {data.get('start_time', '')}\n🏁 {data.get('finish_time', '')}"
                await bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="HTML")
            await message.answer("✅ <b>Данные получены!</b>", parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка: {e}")

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
