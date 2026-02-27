import asyncio
import os
import cv2
import shutil
import numpy as np
import img2pdf
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton

# Bot tokeningizni Railway Variables-dan oladi
TOKEN = os.getenv("TOKEN") or "8733916664:AAGSko0YAtATf6pdluZpobKOdCoycjoB65Y"

bot = Bot(token=TOKEN)
dp = Dispatcher()

BASE_TEMP_DIR = "temp_files"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

user_tasks = {}
user_menu_msg = {}

# --- Klaviaturalar ---

def get_main_reply_keyboard():
    # Bu tugma klaviatura o'rnida har doim turadi
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🚀 Botni qayta ishga tushirish"))
    return builder.as_markup(resize_keyboard=True)

def get_pdf_keyboard(count):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"📄 PDF qilish ({count} ta)", callback_data="make_pdf_normal"))
    builder.row(types.InlineKeyboardButton(text="✨ Tiniqlashtirish (B&W)", callback_data="make_pdf_enhanced"))
    builder.row(types.InlineKeyboardButton(text="🗑 Hammasini o'chirish", callback_data="clear_all"))
    return builder.as_markup()

# --- Tasvirni qayta ishlash ---

def enhance_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Hujjat sifatini oshirish uchun Adaptive Threshold
    enhanced = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 12
    )
    is_success, buffer = cv2.imencode(".jpg", enhanced)
    return buffer.tobytes()

# --- Handlerlar ---

@dp.message(Command("start"))
@dp.message(F.text == "🚀 Botni qayta ishga tushirish")
async def start_cmd(message: types.Message):
    # Foydalanuvchi papkasini tozalash
    user_dir = os.path.join(BASE_TEMP_DIR, str(message.from_user.id))
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    
    await message.answer(
        "👋 **Assalomu alaykum!**\n\n"
        "Men rasmlaringizni sifatli PDF qilib beruvchi botman.\n"
        "🖼 **Menga rasm(lar) yuboring...**",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )

async def send_menu_with_delay(user_id, chat_id):
    await asyncio.sleep(1.5) # Rasmlar yuklanishini kutish
    user_dir = os.path.join(BASE_TEMP_DIR, str(user_id))
    if not os.path.exists(user_dir): return

    photos = [f for f in os.listdir(user_dir) if f.endswith('.jpg')]
    count = len(photos)
    if count == 0: return

    text = f"📸 **{count} ta rasm qabul qilindi.**\n\nQuyidagi amallardan birini tanlang:"
    kb = get_pdf_keyboard(count)

    # Agar oldingi menyu bo'lsa, uni o'chirib yangisini yuboramiz
    if user_id in user_menu_msg:
        try: await bot.delete_message(chat_id, user_menu_msg[user_id])
        except: pass

    msg = await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="Markdown")
    user_menu_msg[user_id] = msg.message_id

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    uid = message.from_user.id
    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))
    if not os.path.exists(user_dir): os.makedirs(user_dir)
    
    file_path = os.path.join(user_dir, f"{message.message_id}.jpg")
    await bot.download(message.photo[-1], destination=file_path)

    # Taymerni yangilash (bir nechta rasm yuborilganda oxirida menyu chiqarish)
    if uid in user_tasks:
        user_tasks[uid].cancel()
    user_tasks[uid] = asyncio.create_task(send_menu_with_delay(uid, message.chat.id))

@dp.callback_query(F.data.startswith("make_pdf_"))
async def process_pdf(callback: types.CallbackQuery):
    uid = callback.from_user.id
    mode = callback.data.split("_")[-1]
    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))

    if not os.path.exists(user_dir) or not os.listdir(user_dir):
        await callback.answer("⚠️ Rasmlar topilmadi, iltimos qayta yuboring.")
        return

    await callback.message.edit_text("⏳ **PDF tayyorlanmoqda, iltimos kuting...**", parse_mode="Markdown")

    try:
        # Rasmlarni tartiblash
        files = sorted([os.path.join(user_dir, f) for f in os.listdir(user_dir)], key=os.path.getmtime)
        pdf_data = []

        for f in files:
            if mode == "enhanced":
                pdf_data.append(enhance_image(f))
            else:
                with open(f, "rb") as img_file:
                    pdf_data.append(img_file.read())

        pdf_bytes = img2pdf.convert(pdf_data)
        final_pdf = BufferedInputFile(pdf_bytes, filename="PDF_Hujjat.pdf")
        
        await callback.message.answer_document(final_pdf, caption="✅ **PDF tayyor bo'ldi!**")
        shutil.rmtree(user_dir)
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.answer(f"❌ Xatolik yuz berdi: {str(e)[:50]}")

@dp.callback_query(F.data == "clear_all")
async def clear_data(callback: types.CallbackQuery):
    uid = callback.from_user.id
    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    await callback.message.edit_text("🗑 Barcha rasmlar tozalandi. Yangi rasm yuborishingiz mumkin.")

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
