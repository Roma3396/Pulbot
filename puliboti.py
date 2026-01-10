import asyncio
import logging
import sqlite3
import re
from datetime import datetime
from flask import Flask
from threading import Thread

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- KONFIGURATSIYA ---
TOKEN = "7696636612:AAF-zbnvHViQtJS5stwYS5Hhnsqnx4P0DRI"
ADMINS = [7829422043, 6881599988]
CHANNELS = [
    {"url": "https://t.me/Fargona_Arenda_Cars", "id": -1002797110799},
    {"url": "https://t.me/FeaF_Helping", "id": -1003155796926},
    {"url": "https://t.me/Disney_Multfilmlar1", "id": -1003646737157}
]

# --- FLASK (Keep Alive uchun) ---
app = Flask('')
@app.route('/')
def home(): return "Bot ishlamoqda!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- DATABASE ---
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()

def init_db():
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, name TEXT, job TEXT, salary INTEGER, 
        dream_name TEXT, dream_price INTEGER, dream_photo TEXT,
        card_bal INTEGER DEFAULT 0, cash_bal INTEGER DEFAULT 0,
        saved_bal INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0, 
        premium_date TEXT, rating_count INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
        type TEXT, category TEXT, amount INTEGER, comment TEXT, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS advances (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
        reason TEXT, amount INTEGER, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS global_stats (key TEXT PRIMARY KEY, value INTEGER)''')
    cursor.execute("INSERT OR IGNORE INTO global_stats VALUES ('total_rating', 0)")
    db.commit()

init_db()

# --- SMART MONEY PARSER ---
def parse_money(text):
    text = text.lower().replace(" ", "").replace(",", "").replace("so'm", "").replace("som", "")
    if 'mln' in text:
        res = re.findall(r"(\d+\.?\d*)", text)
        return int(float(res[0]) * 1000000) if res else 0
    if 'ming' in text:
        res = re.findall(r"(\d+\.?\d*)", text)
        return int(float(res[0]) * 1000) if res else 0
    res = re.findall(r"\d+", text)
    return int("".join(res)) if res else 0

# --- SUBSCRIPTION CHECK ---
async def is_subscribed(bot: Bot, user_id: int):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch['id'], user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

# --- STATES ---
class BotStates(StatesGroup):
    # Registration
    name = State()
    job = State()
    salary = State()
    dream_photo = State()
    dream_details = State()
    # Finance
    add_amount = State()
    spend_reason = State()
    spend_amount = State()
    save_amount = State()
    # Avans
    adv_reason = State()
    adv_amount = State()
    # Settings
    edit_salary = State()
    edit_job = State()
    # Admin
    admin_post = State()
    admin_msg_id = State()
    admin_msg_text = State()
    premium_date_set = State()

# --- KEYBOARDS ---
def main_menu(uid):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="1-Pul qoshish 💰"), KeyboardButton(text="2-Harajat qoshish 💸"))
    builder.row(KeyboardButton(text="3-Kirim chiqim 📊"), KeyboardButton(text="4-Toplangan pul 🎯"))
    builder.row(KeyboardButton(text="5-avans 🏦"), KeyboardButton(text="6-premium 💎"))
    builder.row(KeyboardButton(text="7-murojat 📩"), KeyboardButton(text="👤 sizning malumot"))
    if uid in ADMINS:
        builder.row(KeyboardButton(text="8-Post joylash 📢"), KeyboardButton(text="9-statistika 📈"))
        builder.row(KeyboardButton(text="10-Premium obunachilar 🎖"))
    return builder.as_markup(resize_keyboard=True)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Orqaga")]], resize_keyboard=True)

# --- BOT HANDLERS ---
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(F.text == "⬅️ Orqaga")
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz 🏠", reply_markup=main_menu(message.from_user.id))

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if not await is_subscribed(bot, message.from_user.id):
        kb = InlineKeyboardBuilder()
        for i, ch in enumerate(CHANNELS, 1):
            kb.row(InlineKeyboardButton(text=f"{i}-Kanal 🔗", url=ch['url']))
        kb.row(InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub"))
        await message.answer("Botdan foydalanish uchun quyidagi kanalarga obuna boling 👇", reply_markup=kb.as_markup())
        return

    cursor.execute("SELECT name FROM users WHERE id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        await message.answer(f"Xush kelibsiz, {user[0]}! 👋", reply_markup=main_menu(message.from_user.id))
    else:
        await message.answer("Salom!, men endi siz bilan man. 😊\nKeling birinchi tanishib olamiz,\nIsmingizni yozing. ✍️")
        await state.set_state(BotStates.name)

@dp.callback_query(F.data == "check_sub")
async def sub_callback(call: CallbackQuery, state: FSMContext):
    if await is_subscribed(bot, call.from_user.id):
        await call.message.delete()
        await cmd_start(call.message, state)
    else:
        await call.answer("Hali obuna bolmadingiz! ❌", show_alert=True)

# --- REGISTRATION ---
@dp.message(BotStates.name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(n=message.text)
    await message.answer(f"{message.text} juda chiroyli ism ekan. ✨\nKeling endi nma ish qilishingizni bilsam.")
    await state.set_state(BotStates.job)

@dp.message(BotStates.job)
async def reg_job(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(j=message.text)
    await message.answer(f"{message.text} oho yaxshi kasb egasi ekansiz {data['n']} keling endi qancha maosh olishingizni bilsam shunda sizga koproq yordam bera olaman. 💵")
    await state.set_state(BotStates.salary)

@dp.message(BotStates.salary)
async def reg_salary(message: Message, state: FSMContext):
    s = parse_money(message.text)
    data = await state.get_data()
    await state.update_data(s=s)
    await message.answer(f"{data['n']} siz {data['j']} ekansiz va {s:,} olar ekansiz keling endi nma uchun pul toplamoqchi ekanligingizni bilsam. Menga uni rasmini yuboring. 📸")
    await state.set_state(BotStates.dream_photo)

@dp.message(BotStates.dream_photo, F.photo)
async def reg_photo(message: Message, state: FSMContext):
    await state.update_data(ph=message.photo[-1].file_id)
    await message.answer("oho yaxshi narsa orzi qilibsiz! Keling endi bu narsa nomi va narxini yozing misol: Mashina, 10000000")
    await state.set_state(BotStates.dream_details)

@dp.message(BotStates.dream_details)
async def reg_final(message: Message, state: FSMContext):
    try:
        parts = message.text.split(",")
        d_name = parts[0].strip()
        d_price = parse_money(parts[1])
        data = await state.get_data()
        cursor.execute("INSERT INTO users (id, name, job, salary, dream_name, dream_price, dream_photo) VALUES (?,?,?,?,?,?,?)",
                       (message.from_user.id, data['n'], data['j'], data['s'], d_name, d_price, data['ph']))
        db.commit()
        await message.answer(f"{data['n']} endi biz {d_name}ga birga erishamiz. 🚀", reply_markup=main_menu(message.from_user.id))
        await state.clear()
    except:
        await message.answer("Iltimos namunadagidek yozing! (Nomi, Narxi)")

# --- 1-PUL QOSHISH ---
@dp.message(F.text == "1-Pul qoshish 💰")
async def add_money_start(message: Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Kartaga 💳", callback_data="add_to_card"),
           InlineKeyboardButton(text="Naqdga 💵", callback_data="add_to_cash"))
    await message.answer(f"{message.from_user.first_name} qaysi biriga pul qoshasiz?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("add_to_"))
async def add_money_choice(call: CallbackQuery, state: FSMContext):
    m = "Kartangizga" if "card" in call.data else "Naqdga"
    await state.update_data(target=call.data)
    await call.message.answer(f"Hop endi {m} qancha pul qoshmoqchisiz {call.from_user.first_name}?", reply_markup=back_kb())
    await state.set_state(BotStates.add_amount)

@dp.message(BotStates.add_amount)
async def add_money_finish(message: Message, state: FSMContext):
    if message.text == "⬅️ Orqaga": return
    val = parse_money(message.text)
    data = await state.get_data()
    col = "card_bal" if "card" in data['target'] else "cash_bal"
    cursor.execute(f"UPDATE users SET {col} = {col} + ? WHERE id = ?", (val, message.from_user.id))
    cursor.execute("INSERT INTO history (user_id, type, category, amount, date) VALUES (?,?,?,?,?)",
                   (message.from_user.id, "Kirim", col, val, datetime.now().strftime("%d.%m.%Y")))
    db.commit()
    await message.answer(f"Muvaffaqiyatli qoshildi! ✅", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# --- 2-HARAJAT QOSHISH ---
@dp.message(F.text == "2-Harajat qoshish 💸")
async def spend_start(message: Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Kartadan 💳", callback_data="sp_from_card"),
           InlineKeyboardButton(text="Naqtdan 💵", callback_data="sp_from_cash"))
    await message.answer(f"{message.from_user.first_name} bugun quyidagilardan qay biridan haranat qilasiz?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("sp_from_"))
async def spend_choice(call: CallbackQuery, state: FSMContext):
    await state.update_data(src=call.data)
    await call.message.answer(f"{call.from_user.first_name} bugun nimga harajat qilishingizni yozing.", reply_markup=back_kb())
    await state.set_state(BotStates.spend_reason)

@dp.message(BotStates.spend_reason)
async def spend_reason_get(message: Message, state: FSMContext):
    await state.update_data(res=message.text)
    await message.answer(f"{message.text}ga qancha pul sarfladingiz?")
    await state.set_state(BotStates.spend_amount)

@dp.message(BotStates.spend_amount)
async def spend_finish(message: Message, state: FSMContext):
    val = parse_money(message.text)
    data = await state.get_data()
    col = "card_bal" if "card" in data['src'] else "cash_bal"
    cursor.execute(f"UPDATE users SET {col} = {col} - ? WHERE id = ?", (val, message.from_user.id))
    cursor.execute("INSERT INTO history (user_id, type, category, amount, comment, date) VALUES (?,?,?,?,?,?)",
                   (message.from_user.id, "Chiqim", col, val, data['res'], datetime.now().strftime("%d.%m.%Y")))
    db.commit()
    await message.answer("Harajat saqlandi! 📉", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# --- 3-KIRIM CHIQIM ---
@dp.message(F.text == "3-Kirim chiqim 📊")
async def show_history(message: Message):
    cursor.execute("SELECT type, comment, amount, category, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 20", (message.from_user.id,))
    rows = cursor.fetchall()
    cursor.execute("SELECT card_bal, cash_bal FROM users WHERE id=?", (message.from_user.id,))
    ub = cursor.fetchone()
    
    text = "📊 Oxirgi amallar:\n\n"
    for r in rows:
        icon = "➕" if r[0]=="Kirim" else "➖"
        text += f"{icon} {r[4]}: {r[2]:,} som ({r[1] if r[1] else r[3]})\n"
    
    text += f"\n💳 Karta: {ub[0]:,} som\n💵 Naqd: {ub[1]:,} som"
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️", callback_data="hist_prev_0"),
           InlineKeyboardButton(text="Toplash 💰", callback_data="save_money_start"),
           InlineKeyboardButton(text="➡️", callback_data="hist_next_20"))
    await message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "save_money_start")
async def save_money_start(call: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Kartadan", callback_data="save_card"),
           InlineKeyboardButton(text="Naqdan", callback_data="save_cash"))
    await call.message.answer("Qaysi biridan pulni toplanganlarga otkaz moqchisiz?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("save_"))
async def save_money_choice(call: CallbackQuery, state: FSMContext):
    await state.update_data(save_src=call.data)
    await call.message.answer("Orzuyinga toplayotgan pulinga qancha pul qoshmoqchisan?")
    await state.set_state(BotStates.save_amount)

@dp.message(BotStates.save_amount)
async def save_money_finish(message: Message, state: FSMContext):
    val = parse_money(message.text)
    data = await state.get_data()
    col = "card_bal" if "card" in data['save_src'] else "cash_bal"
    cursor.execute(f"UPDATE users SET {col} = {col} - ?, saved_bal = saved_bal + ? WHERE id = ?", (val, val, message.from_user.id))
    db.commit()
    await message.answer("Pul orzu uchun toplandi! 🎯", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# --- 4-TOPLANGAN PUL ---
@dp.message(F.text == "4-Toplangan pul 🎯")
async def dream_status(message: Message):
    cursor.execute("SELECT name, dream_name, dream_price, dream_photo, saved_bal FROM users WHERE id=?", (message.from_user.id,))
    u = cursor.fetchone()
    qolgan = u[2] - u[4]
    text = f"🎯 Orzu: {u[1]}\n💰 Narxi: {u[2]:,}\n✅ Toplandi: {u[4]:,}\n⏳ Qoldi: {qolgan:,}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Erishdim 🎉", callback_data="dream_done"),
           InlineKeyboardButton(text="Erisha olmadim ❌", callback_data="dream_fail"))
    await bot.send_photo(message.chat.id, u[3], caption=text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "dream_done")
async def dream_done(call: CallbackQuery):
    cursor.execute("SELECT name, dream_name FROM users WHERE id=?", (call.from_user.id,))
    u = cursor.fetchone()
    for admin in ADMINS:
        await bot.send_message(admin, f"🎉 Obunachi {u[0]} o'z orzusiga ({u[1]}) erishdi!")
    await call.message.answer(f"{u[0]} Men bilgan edim seni {u[1]}ga erisha olishingni tabriklayman hursand boldim! 😊", 
                             reply_markup=InlineKeyboardBuilder().button(text="Yana orzu qoshish ➕", callback_data="reset_dream").as_markup())

@dp.callback_query(F.data == "dream_fail")
async def dream_fail(call: CallbackQuery):
    cursor.execute("SELECT name, dream_name FROM users WHERE id=?", (call.from_user.id,))
    u = cursor.fetchone()
    await call.message.answer(f"{u[0]} Hechqisi yoq {u[1]}ga erisholmagan bolasngham harakatdan toxtama kel boshqa narsaga pul yegamiz.",
                             reply_markup=InlineKeyboardBuilder().button(text="Yana orzu qoshish ➕", callback_data="reset_dream").as_markup())

@dp.callback_query(F.data == "reset_dream")
async def reset_dream(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Yangi orzu rasmini yuboring 📸")
    await state.set_state(BotStates.dream_photo)

# --- 5-AVANS ---
@dp.message(F.text == "5-avans 🏦")
async def avans_menu(message: Message):
    text = f"{message.from_user.first_name} Bu bolim agarda sen dokonda ishlasang hali olmagan oyligingdan narsalar harit qilishing mumkin yoki pul olishing."
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Avans olish 💵", callback_data="adv_take"),
           InlineKeyboardButton(text="Avanslar royxati 📄", callback_data="adv_list"))
    await message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "adv_take")
async def adv_take_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer(f"{call.from_user.first_name} nmaga avans olganingni yoz misol: Bozorlik uchun")
    await state.set_state(BotStates.adv_reason)

@dp.message(BotStates.adv_reason)
async def adv_reason_get(message: Message, state: FSMContext):
    await state.update_data(ar=message.text)
    await message.answer(f"Hop {message.from_user.first_name} {message.text} uchun qancha pul yozdirding?")
    await state.set_state(BotStates.adv_amount)

@dp.message(BotStates.adv_amount)
async def adv_finish(message: Message, state: FSMContext):
    val = parse_money(message.text)
    data = await state.get_data()
    cursor.execute("INSERT INTO advances (user_id, reason, amount, date) VALUES (?,?,?,?)",
                   (message.from_user.id, data['ar'], val, datetime.now().strftime("%d.%m.%Y")))
    db.commit()
    await message.answer("Avans yozildi! ✅", reply_markup=main_menu(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "adv_list")
async def adv_list_show(call: CallbackQuery):
    cursor.execute("SELECT reason, amount, date FROM advances WHERE user_id=?", (call.from_user.id,))
    rows = cursor.fetchall()
    cursor.execute("SELECT salary FROM users WHERE id=?", (call.from_user.id,))
    sal = cursor.fetchone()[0]
    total_adv = sum(r[1] for r in rows)
    
    text = "📄 Avanslar:\n"
    for r in rows: text += f"- {r[2]}: {r[0]} ({r[1]:,} som)\n"
    text += f"\n💰 Oylikdan qoldi: {(sal - total_adv):,} som"
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️", callback_data="adv_p"),
           InlineKeyboardButton(text="Oylik oldim ✅", callback_data="adv_clear"),
           InlineKeyboardButton(text="➡️", callback_data="adv_n"))
    await call.message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "adv_clear")
async def adv_clear(call: CallbackQuery):
    cursor.execute("SELECT SUM(amount) FROM advances WHERE user_id=?", (call.from_user.id,))
    total = cursor.fetchone()[0] or 0
    cursor.execute("SELECT salary FROM users WHERE id=?", (call.from_user.id,))
    sal = cursor.fetchone()[0]
    qolgan = sal - total
    cursor.execute("UPDATE users SET cash_bal = cash_bal + ? WHERE id = ?", (qolgan, call.from_user.id))
    cursor.execute("DELETE FROM advances WHERE user_id=?", (call.from_user.id,))
    db.commit()
    await call.message.answer("Oylik naqd balansga qoshildi va avanslar tozalandi! 🧼")

# --- PREMIUM (6) ---
@dp.message(F.text == "6-premium 💎")
async def premium_info(message: Message):
    cursor.execute("SELECT name FROM users WHERE id=?", (message.from_user.id,))
    n = cursor.fetchone()[0]
    await message.answer(f"Salom {n} premium sotib olish narxi 5000 som\nManashu karta raqamga pul yuboring va shu yerga tolov chekini yuboring\nKarta raqam: 0000 0000 0000\nKarta egasi: G. T.")

@dp.message(F.photo, F.caption.contains("chek") | F.caption.is_(None))
async def handle_payment(message: Message, state: FSMContext):
    if await state.get_state() == BotStates.dream_photo: return
    for admin in ADMINS:
        kb = InlineKeyboardBuilder().button(text="Premium berish 🎖", callback_data=f"give_prem_{message.from_user.id}").as_markup()
        await bot.send_photo(admin, message.photo[-1].file_id, caption=f"Tolov cheki: {message.from_user.id}", reply_markup=kb)
    await message.answer("Chek adminga yuborildi! ⏳")

@dp.callback_query(F.data.startswith("give_prem_"))
async def admin_prem_date(call: CallbackQuery, state: FSMContext):
    uid = call.data.split("_")[2]
    await state.update_data(p_uid=uid)
    await call.message.answer("Premiumni amal qilish sanasini yuboring (misol 14.04.2025):")
    await state.set_state(BotStates.premium_date_set)

@dp.message(BotStates.premium_date_set)
async def admin_prem_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("UPDATE users SET is_premium=1, premium_date=? WHERE id=?", (message.text, data['p_uid']))
    db.commit()
    await bot.send_message(data['p_uid'], f"Tabriklaymiz! Premium faollashdi. Muddati: {message.text} gacha.")
    await message.answer("Premium berildi! ✅")
    await state.clear()

# --- ADMIN PANEL (9, 10, 8) ---
@dp.message(F.text == "9-statistika 📈")
async def admin_stats(message: Message):
    if message.from_user.id not in ADMINS: return
    cursor.execute("SELECT COUNT(*) FROM users")
    uc = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM global_stats WHERE key='total_rating'")
    tr = cursor.fetchone()[0]
    cursor.execute("SELECT id, name, salary, dream_name FROM users LIMIT 20")
    rows = cursor.fetchall()
    
    res = f"📈 Statistika:\nJami ball: {tr}\nObunachilar: {uc}\n\n"
    for r in rows: res += f"ID:{r[0]} | {r[1]} | {r[2]:,} | {r[3]}\n"
    
    kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⬅️", callback_data="st_p"), InlineKeyboardButton(text="➡️", callback_data="st_n"))
    await message.answer(res, reply_markup=kb.as_markup())

@dp.message(F.text == "10-Premium obunachilar 🎖")
async def admin_premiums(message: Message):
    if message.from_user.id not in ADMINS: return
    cursor.execute("SELECT id, name, premium_date FROM users WHERE is_premium=1 LIMIT 20")
    rows = cursor.fetchall()
    res = "🎖 Premium obunachilar:\n"
    for r in rows: res += f"ID:{r[0]} | {r[1]} | Tugaydi: {r[2]}\n"
    kb = InlineKeyboardBuilder().button(text="Premiumni olish ⚠️", callback_data="revoke_expired").as_markup()
    await message.answer(res, reply_markup=kb)

@dp.callback_query(F.data == "revoke_expired")
async def revoke_prem(call: CallbackQuery):
    cursor.execute("UPDATE users SET is_premium=0 WHERE is_premium=1") # Bu yerda sanani tekshirish logikasini qoshish mumkin
    db.commit()
    await call.message.answer("Muddati otganlar (test rejimi: hamma) olib tashlandi.")

# --- SIZNING MALUMOT ---
@dp.message(F.text == "👤 sizning malumot")
async def user_info(message: Message):
    cursor.execute("SELECT name, job, salary FROM users WHERE id=?", (message.from_user.id,))
    u = cursor.fetchone()
    text = f"👤 Ism: {u[0]}\n💼 Kasb: {u[1]}\n💵 Maosh: {u[2]:,}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Maoshni ozgartirish 💰", callback_data="edit_s"),
           InlineKeyboardButton(text="Kasbni ozgartirish 💼", callback_data="edit_j"))
    await message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "edit_s")
async def edit_s(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Yangi maoshni yozing:")
    await state.set_state(BotStates.edit_salary)

@dp.message(BotStates.edit_salary)
async def edit_s_finish(message: Message, state: FSMContext):
    s = parse_money(message.text)
    cursor.execute("UPDATE users SET salary=? WHERE id=?", (s, message.from_user.id))
    db.commit()
    await message.answer("Yangilandi! ✅", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# --- ADMIN POST VA HABAR ---
@dp.message(F.text == "8-Post joylash 📢")
async def admin_post_menu(message: Message):
    if message.from_user.id not in ADMINS: return
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Oddiy post", callback_data="post_simple"),
           InlineKeyboardButton(text="Baholash posti", callback_data="post_rate"),
           InlineKeyboardButton(text="Habar", callback_data="post_msg"))
    await message.answer("Post turini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "post_rate")
async def admin_post_rate(call: CallbackQuery):
    cursor.execute("SELECT id, name FROM users")
    users = cursor.fetchall()
    for u in users:
        kb = InlineKeyboardBuilder()
        for i in range(1, 11): kb.add(InlineKeyboardButton(text=str(i), callback_data=f"rate_{i}"))
        kb.adjust(5)
        try: await bot.send_message(u[0], f"{u[1]} iltimos meni qollab quvatlash uchun meni 1 dan 10 balgacha bahola 😊", reply_markup=kb.as_markup())
        except: pass
    await call.message.answer("Baholash posti yuborildi! ✅")

@dp.callback_query(F.data.startswith("rate_"))
async def rate_handler(call: CallbackQuery):
    cursor.execute("SELECT rating_count FROM users WHERE id=?", (call.from_user.id,))
    if cursor.fetchone()[0] > 0:
        await call.answer("Faqat 1 marta baholash mumkin! ⚠️")
        return
    val = int(call.data.split("_")[1])
    cursor.execute("UPDATE global_stats SET value = value + ? WHERE key='total_rating'", (val,))
    cursor.execute("UPDATE users SET rating_count = 1 WHERE id=?", (call.from_user.id,))
    db.commit()
    await call.message.edit_text("Raxmat! Bahoingiz qabul qilindi. 😇")

# --- MAIN ---
async def main():
    keep_alive()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
