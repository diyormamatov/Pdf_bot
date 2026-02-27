import asyncio
import os
import cv2
import shutil
import numpy as np
import img2pdf
import aspose.words as aw  # Linux uchun to'g'ri kutubxona
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile, FSInputFile

# 1. Bot tokeningizni kiriting
TOKEN = os.getenv("TOKEN") or "8733916664:AAGSko0YAtATf6pdluZpobKOdCoycjoB65Y"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Vaqtinchalik fayllar uchun asosiy papka
BASE_TEMP_DIR = "temp_files"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

user_modes = {}
user_tasks = {}
user_menu_msg = {}

# --- Klaviaturalar ---

def start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🖼 Rasmni PDF qilish", callback_data="mode_image"))
    builder.row(types.InlineKeyboardButton(text="📝 Wordni PDF qilish", callback_data="mode_word"))
    return builder.as_markup()

def main_keyboard(count):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"📄 PDF qilish ({count} ta)", callback_data="make_pdf_normal"))
    builder.row(types.InlineKeyboardButton(text="🖋 Tiniqlashtirish (Qora-Oq)", callback_data="make_pdf_enhanced"))
    builder.row(types.InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_all"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main"))
    return builder.as_markup()

# --- Yordamchi funksiyalar ---

def enhance_image_path(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 10
    )
    is_success, buffer = cv2.imencode(".jpg", enhanced)
    return buffer.tobytes()

def convert_word_to_pdf_linux(input_path, output_path):
    """Linuxda Wordni PDF qilish uchun Aspose funksiyasi"""
    doc = aw.Document(input_path)
    doc.save(output_path)

async def send_final_menu(user_id, chat_id):
    await asyncio.sleep(2.0)
    user_dir = os.path.join(BASE_TEMP_DIR, str(user_id))
    if not os.path.exists(user_dir): return

    photos = [f for f in os.listdir(user_dir) if f.endswith('.jpg')]
    count = len(photos)
    if count == 0: return

    text = f"✅ {count} ta rasm tayyor.\n\nPDF turini tanlang:"
    kb = main_keyboard(count)

    if user_id in user_menu_msg:
        try:
            await bot.edit_message_text(text, chat_id, user_menu_msg[user_id], reply_markup=kb)
        except:
            msg = await bot.send_message(chat_id, text, reply_markup=kb)
            user_menu_msg[user_id] = msg.message_id
    else:
        msg = await bot.send_message(chat_id, text, reply_markup=kb)
        user_menu_msg[user_id] = msg.message_id

# --- Handlerlar ---

@dp.message(Command("start"))
async def start(message: types.Message):
    user_modes[message.from_user.id] = None
    await message.answer("Xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=start_keyboard())

@dp.callback_query(F.data == "back_to_main")
async def back_main(callback: types.CallbackQuery):
    user_modes[callback.from_user.id] = None
    await callback.message.edit_text("Kerakli bo'limni tanlang:", reply_markup=start_keyboard())

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(callback: types.CallbackQuery):
    mode = callback.data.split("_")[1]
    user_modes[callback.from_user.id] = mode
    if mode == "image":
        await callback.message.edit_text("Rasmlarni yuboring (bir nechta yuborishingiz mumkin):")
    else:
        await callback.message.edit_text("Word (.docx) faylini yuboring:")

@dp.message(F.photo)
async def handle_photos(message: types.Message):
    uid = message.from_user.id
    if user_modes.get(uid) != "image":
        await message.answer("Iltimos, avval 'Rasmni PDF qilish' bo'limini tanlang.")
        return

    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))
    if not os.path.exists(user_dir): os.makedirs(user_dir)
    
    photo_path = os.path.join(user_dir, f"{message.message_id}.jpg")
    await bot.download(message.photo[-1], destination=photo_path)

    if uid in user_tasks: user_tasks[uid].cancel()
    user_tasks[uid] = asyncio.create_task(send_final_menu(uid, message.chat.id))

@dp.message(F.document)
async def handle_docs(message: types.Message):
    uid = message.from_user.id
    if user_modes.get(uid) != "word":
        await message.answer("Iltimos, avval 'Wordni PDF qilish' bo'limini tanlang.")
        return

    if not message.document.file_name.endswith(".docx"):
        await message.answer("Faqat .docx formatidagi fayllarni qabul qilaman!")
        return

    wait_msg = await message.answer("⏳ Word PDF-ga o'tkazilmoqda...")
    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))
    if not os.path.exists(user_dir): os.makedirs(user_dir)

    input_path = os.path.join(user_dir, message.document.file_name)
    output_path = input_path.replace(".docx", ".pdf")

    await bot.download(message.document, destination=input_path)

    try:
        # Linuxda ishlovchi konvertatsiya
        await asyncio.to_thread(convert_word_to_pdf_linux, input_path, output_path)
        
        pdf_file = FSInputFile(output_path)
        await message.answer_document(pdf_file, caption="✅ Word PDF-ga muvaffaqiyatli o'tkazildi!")
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {str(e)}")
    finally:
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        await wait_msg.delete()

@dp.callback_query(F.data.startswith("make_pdf_"))
async def process_pdf(callback: types.CallbackQuery):
    uid = callback.from_user.id
    mode = callback.data.split("_")[-1]
    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))

    if not os.path.exists(user_dir):
        await callback.answer("Rasmlar topilmadi!")
        return

    await callback.message.edit_text("⏳ PDF tayyorlanmoqda...")

    try:
        photo_files = sorted([os.path.join(user_dir, f) for f in os.listdir(user_dir) if f.endswith('.jpg')], 
                            key=os.path.getmtime)
        
        pdf_images = []
        for p in photo_files:
            if mode == "enhanced":
                pdf_images.append(enhance_image_path(p))
            else:
                with open(p, "rb") as f:
                    pdf_images.append(f.read())

        pdf_bytes = img2pdf.convert(pdf_images)
        pdf_file = BufferedInputFile(pdf_bytes, filename="Tayyor_fayl.pdf")
        
        await callback.message.answer_document(pdf_file, caption="Sizning PDFingiz tayyor!")
        shutil.rmtree(user_dir)
        if uid in user_menu_msg: del user_menu_msg[uid]
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.answer(f"Xatolik: {str(e)[:50]}")

@dp.callback_query(F.data == "clear_all")
async def clear(callback: types.CallbackQuery):
    uid = callback.from_user.id
    user_dir = os.path.join(BASE_TEMP_DIR, str(uid))
    if os.path.exists(user_dir): shutil.rmtree(user_dir)
    if uid in user_menu_msg: del user_menu_msg[uid]
    await callback.message.edit_text("Hamma rasmlar o'chirildi.", reply_markup=start_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
