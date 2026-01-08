import asyncio
import logging
import sqlite3
import re
from datetime import datetime
from threading import Thread
from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- FLASK SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Active!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- KONFIGURATSIYA ---
TOKEN = "7693190148:AAGTjp2Lb4HkNenC2e9EYUx3BebFb4p5kIQ"
ADMIN_ID = [7829422043, 6881599988]
CHANNELS = [
    {"link": "@FeaF_Helping", "id": -1003155796926},
    {"link": "https://t.me/Disney_Multfilmlar1", "id": -1003646737157},
    {"link": "https://t.me/Fargona_Arenda_Cars", "id": -1002797110799}
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("pul_toplaymiz.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, name TEXT, job TEXT, salary TEXT, 
        balance REAL DEFAULT 0, saved_money REAL DEFAULT 0,
        dream_name TEXT, dream_price REAL, dream_photo TEXT,
        usage_count INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0,
        premium_date TEXT, rating INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS history (
        user_id INTEGER, type TEXT, reason TEXT, amount REAL, date TEXT)""")
    conn.commit()
    conn.close()

init_db()

def parse_money(text):
    text = text.lower().replace(" ", "").replace(",", "").replace("'", "")
    multipliers = {'ming': 1000, 'mln': 1000000, 'million': 1000000, 'k': 1000}
    num_match = re.search(r"(\d+\.?\d*)", text)
    if not num_match: return None
    val = float(num_match.group(1))
    for key, mult in multipliers.items():
        if key in text: val *= mult
    return val

class Form(StatesGroup):
    name = State()
    job = State()
    salary = State()
    dream_photo = State()
    dream_name = State()
    dream_price = State()
    add_money = State()
    exp_reason = State()
    exp_amount = State()
    murojaat = State()
    admin_answer = State()
    admin_post = State()
    admin_msg_user_id = State()
    admin_msg_text = State()
    premium_chek = State()
    premium_date_give = State()

def get_main_kb(user_id):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💰 Pul qo'shish"), KeyboardButton(text="💸 Harajat qo'shish"))
    builder.add(KeyboardButton(text="📊 Kirim chiqim"), KeyboardButton(text="🎯 To'plangan pul"))
    builder.add(KeyboardButton(text="💎 Premium"), KeyboardButton(text="✍️ Murojat"))
    if user_id == ADMIN_ID:
        builder.add(KeyboardButton(text="⚙️ Admin Panel"))
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def back_btn():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Orqaga")]], resize_keyboard=True)

def admin_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📢 Post joylash"), KeyboardButton(text="📈 Statistika"))
    builder.add(KeyboardButton(text="👑 Premium obunachilar"), KeyboardButton(text="⬅️ Bosh menyu"))
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    conn = sqlite3.connect("pul_toplaymiz.db")
    user = conn.execute("SELECT id FROM users WHERE id=?", (message.from_user.id,)).fetchone()
    conn.close()
    if not user:
        builder = InlineKeyboardBuilder()
        for idx, ch in enumerate(CHANNELS, 1):
            builder.row(types.InlineKeyboardButton(text=f"{idx}-Kanal", url=ch['link'] if 'http' in ch['link'] else f"https://t.me/{ch['link'][1:]}"))
        builder.row(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
        await message.answer("👋 Salom! Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=builder.as_markup())
    else:
        await message.answer("Xush kelibsiz! Davom etamiz 🚀", reply_markup=get_main_kb(message.from_user.id))

@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: types.CallbackQuery, state: FSMContext):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch['id'], call.from_user.id)
            if member.status in ["left", "kicked"]:
                return await call.answer("❌ Hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
        except: pass
    await call.message.answer("Salom! Endi men siz bilanman, biz birgalikda hamma narsaga erishamiz. Keling tanishib olamiz.\n\nBirinchi Ismingizni yozing:")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"✨ {message.text} ismingiz chiroyli ekan. Keling endi nima ish qilishingizni ayting:")
    await state.set_state(Form.job)

@dp.message(Form.job)
async def process_job(message: types.Message, state: FSMContext):
    await state.update_data(job=message.text)
    data = await state.get_data()
    await message.answer(f"💼 Oho yaxshi kasb egasi ekansiz {data['name']}, oylik maoshingizni yozing:")
    await state.set_state(Form.salary)

@dp.message(Form.salary)
async def process_salary(message: types.Message, state: FSMContext):
    await state.update_data(salary=message.text)
    data = await state.get_data()
    await message.answer(f"💰 Xo'sh {data['name']}, siz {data['job']} bo'lib ishlar ekansiz. Keling nimaga pul to'plashingizni bilib olsak. Uni rasmini yuboring:")
    await state.set_state(Form.dream_photo)

@dp.message(Form.dream_photo, F.photo)
async def process_dream_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("🤩 Vou bu zo'rku! Endi orzungiz nomi va narxini yozing (Masalan: Mashina, 100 mln):")
    await state.set_state(Form.dream_name)

@dp.message(Form.dream_name)
async def process_dream_final(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split(",")
        name = parts[0].strip()
        price = parse_money(parts[1].strip())
        if not price: raise ValueError
        data = await state.get_data()
        conn = sqlite3.connect("pul_toplaymiz.db")
        conn.execute("INSERT OR REPLACE INTO users (id, name, job, salary, dream_photo, dream_name, dream_price) VALUES (?,?,?,?,?,?,?)",
                     (message.from_user.id, data['name'], data['job'], data['salary'], data['photo'], name, price))
        conn.commit()
        conn.close()
        await message.answer("✅ Jarayonni boshlaymiz!", reply_markup=get_main_kb(message.from_user.id))
        await state.clear()
    except:
        await message.answer("Iltimos, namunadagidek yozing: Nom, Narx (Masalan: Uy, 500 mln)")
@dp.message(F.text == "⬅️ Orqaga")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh menyu", reply_markup=get_main_kb(message.from_user.id))

@dp.message(F.text == "💰 Pul qo'shish")
async def add_money_start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("pul_toplaymiz.db")
    u = conn.execute("SELECT name, usage_count, is_premium FROM users WHERE id=?", (message.from_user.id,)).fetchone()
    conn.close()
    if u[2] == 0 and u[1] >= 20:
        return await message.answer("🚫 Limit tugadi. Premium sotib oling!")
    await message.answer(f"💵 {u[0]}, hisobingizga qancha qo'shamiz?", reply_markup=back_btn())
    await state.set_state(Form.add_money)

@dp.message(Form.add_money)
async def add_money_final(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga": return await go_back(message, state)
    val = parse_money(message.text)
    if val:
        conn = sqlite3.connect("pul_toplaymiz.db")
        conn.execute("UPDATE users SET balance = balance + ?, usage_count = usage_count + 1 WHERE id=?", (val, message.from_user.id))
        conn.execute("INSERT INTO history VALUES (?,?,?,?,?)", (message.from_user.id, "kirim", "Hisobni to'ldirish", val, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Balansga {val:,.0f} so'm qo'shildi!", reply_markup=get_main_kb(message.from_user.id))
        await state.clear()
    else: await message.answer("Miqdorni to'g'ri kiriting!")

@dp.message(F.text == "💸 Harajat qo'shish")
async def exp_start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("pul_toplaymiz.db")
    u = conn.execute("SELECT name FROM users WHERE id=?", (message.from_user.id,)).fetchone()
    conn.close()
    await message.answer(f"💸 {u[0]}, bugun nima uchun harajat qildingiz?", reply_markup=back_btn())
    await state.set_state(Form.exp_reason)

@dp.message(Form.exp_reason)
async def exp_reason_got(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga": return await go_back(message, state)
    await state.update_data(reason=message.text)
    await message.answer("Narxini kiriting:", reply_markup=back_btn())
    await state.set_state(Form.exp_amount)

@dp.message(Form.exp_amount)
async def exp_final(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga": return await go_back(message, state)
    val = parse_money(message.text)
    if val:
        data = await state.get_data()
        conn = sqlite3.connect("pul_toplaymiz.db")
        conn.execute("UPDATE users SET balance = balance - ? WHERE id=?", (val, message.from_user.id))
        conn.execute("INSERT INTO history VALUES (?,?,?,?,?)", (message.from_user.id, "chiqim", data['reason'], val, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
        await message.answer("✅ Harajat qabul qilindi!", reply_markup=get_main_kb(message.from_user.id))
        await state.clear()
    else: await message.answer("Raqam kiriting!")

@dp.message(F.text == "📊 Kirim chiqim")
async def show_history(message: types.Message):
    conn = sqlite3.connect("pul_toplaymiz.db")
    u = conn.execute("SELECT name, balance FROM users WHERE id=?", (message.from_user.id,)).fetchone()
    h = conn.execute("SELECT type, reason, amount, date FROM history WHERE user_id=? ORDER BY date DESC LIMIT 5", (message.from_user.id,)).fetchall()
    conn.close()
    text = f"📊 {u[0]}, oxirgi amallar:\n\n"
    for item in h:
        icon = "➕" if item[0] == "kirim" else "➖"; text += f"{icon} {item[3]} | {item[1]}: {item[2]:,.0f} so'm\n"
    text += f"\n💰 Balans: {u[1]:,.0f} so'm"
    kb = InlineKeyboardBuilder(); kb.button(text="📥 Toplash", callback_data="save_to_dream")
    await message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "save_to_dream")
async def save_to_dream(call: types.CallbackQuery):
    conn = sqlite3.connect("pul_toplaymiz.db")
    u = conn.execute("SELECT balance FROM users WHERE id=?", (call.from_user.id,)).fetchone()
    if u[0] > 0:
        conn.execute("UPDATE users SET saved_money = saved_money + balance, balance = 0 WHERE id=?", (call.from_user.id,))
        conn.commit(); await call.message.answer("🎯 Ortgan pullar orzu uchun jamg'arildi!")
    else: await call.answer("Tejaydigan pulingiz yo'q!", show_alert=True)
    conn.close()

@dp.message(F.text == "🎯 To'plangan pul")
async def show_dream_status(message: types.Message):
    conn = sqlite3.connect("pul_toplaymiz.db")
    u = conn.execute("SELECT dream_photo, dream_name, dream_price, saved_money FROM users WHERE id=?", (message.from_user.id,)).fetchone()
    conn.close()
    if not u or not u[1]: return await message.answer("Sizda faol orzu yo'q.")
    qoldi = max(0, u[2] - u[3])
    text = f"🎯 Orzu: {u[1]}\n💰 Narxi: {u[2]:,.0f} so'm\n📦 To'plandi: {u[3]:,.0f} so'm\n⌛ Qoldi: {qoldi:,.0f} so'm"
    kb = InlineKeyboardBuilder(); kb.button(text="✅ Erishdim", callback_data="dream_won"); kb.button(text="❌ Erisha olmadim", callback_data="dream_lost")
    await bot.send_photo(message.chat.id, u[0], caption=text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dream_"))
async def dream_result(call: types.CallbackQuery, state: FSMContext):
    conn = sqlite3.connect("pul_toplaymiz.db"); u = conn.execute("SELECT name, salary, job FROM users WHERE id=?", (call.from_user.id,)).fetchone()
    if call.data == "dream_won": text = f"🎉 {u[0]}, siz {u[1]} maoshingiz bilan orzungizga erishdingiz!"
    else: text = f"😔 {u[0]} do'stim, afsusdaman. Lekin sen {u[2]}sanku!"
    conn.execute("UPDATE users SET dream_name=NULL, dream_photo=NULL, saved_money=0 WHERE id=?", (call.from_user.id,))
    conn.commit(); conn.close()
    kb = InlineKeyboardBuilder(); kb.button(text="✨ Yana orzu qo'shish", callback_data="new_dream_start")
    await call.message.answer(text, reply_markup=kb.as_markup()); await call.answer()

@dp.callback_query(F.data == "new_dream_start")
async def new_dream_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📸 Yangi orzungiz rasmini yuboring:"); await state.set_state(Form.dream_photo)

# --- PREMIUM (YANGI MANTIQ: CHEKNI SHU YERDA YUBORISH) ---
@dp.message(F.text == "💎 Premium")
async def premium_info(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("pul_toplaymiz.db"); u = conn.execute("SELECT name, dream_name FROM users WHERE id=?", (message.from_user.id,)).fetchone(); conn.close()
    await message.answer(f"Salom {u[0]}! Muloqot pullik qilingan. Birga {u[1]}ga erishamiz!\n\n💳 Karta: 8600 3141 6626 3543\n👤 Egasi: G. T.\n💰 Summa: 5000 so'm\n\nIltimos, to'lov chekini (rasmini) shu yerga yuboring:", reply_markup=back_btn())
    await state.set_state(Form.premium_chek)

@dp.message(Form.premium_chek, F.photo)
async def process_premium_chek(message: types.Message, state: FSMContext):
    kb = InlineKeyboardBuilder(); kb.button(text="👑 Premium berish", callback_data=f"give_prem_{message.from_user.id}")
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"💰 TO'LOV CHEKI!\nFoydalanuvchi ID: {message.from_user.id}", reply_markup=kb.as_markup())
    await message.answer("✅ Chek adminga yuborildi! Tasdiqlashni kuting.", reply_markup=get_main_kb(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data.startswith("give_prem_"))
async def admin_give_prem_start(call: types.CallbackQuery, state: FSMContext):
    uid = call.data.split("_")[2]; await state.update_data(prem_target=uid)
    await call.message.answer("Premium tugash sanasini kiriting (Masalan: 14.04.2025):")
    await state.set_state(Form.premium_date_give); await call.answer()

@dp.message(Form.premium_date_give)
async def admin_give_prem_final(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data(); uid = data['prem_target']
    conn = sqlite3.connect("pul_toplaymiz.db")
    conn.execute("UPDATE users SET is_premium=1, premium_date=? WHERE id=?", (message.text, uid))
    conn.commit(); conn.close()
    try: await bot.send_message(uid, f"🎊 Tabriklaymiz! Sizga {message.text} gacha Premium tarif berildi!")
    except: pass
    await message.answer("✅ Foydalanuvchiga premium berildi!"); await state.clear()

@dp.message(F.text == "✍️ Murojat")
async def muro_start(message: types.Message, state: FSMContext):
    await message.answer("Adminlarga murojatingizni yozing:", reply_markup=back_btn()); await state.set_state(Form.murojaat)

@dp.message(Form.murojaat)
async def muro_final(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga": return await go_back(message, state)
    kb = InlineKeyboardBuilder(); kb.button(text="Javob berish", callback_data=f"reply_{message.from_user.id}")
    await bot.send_message(ADMIN_ID, f"📩 Murojaat: {message.text}\nID: {message.from_user.id}", reply_markup=kb.as_markup())
    await message.answer("✅ Murojatingiz yuborildi!", reply_markup=get_main_kb(message.from_user.id)); await state.clear()

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_main(message: types.Message):
    if message.from_user.id == ADMIN_ID: await message.answer("Admin Paneli", reply_markup=admin_kb())

@dp.message(F.text == "📢 Post joylash")
async def admin_post_type(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder(); kb.button(text="Oddiy post", callback_data="post_1"); kb.button(text="Baho posti", callback_data="post_2"); kb.button(text="Habar (ID orqali)", callback_data="post_3"); kb.adjust(1)
    await message.answer("Post turini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("post_"))
async def admin_post_actions(call: types.CallbackQuery, state: FSMContext):
    action = call.data.split("_")[1]
    if action == "1": await call.message.answer("Post matnini yuboring:"); await state.set_state(Form.admin_post)
    elif action == "2":
        conn = sqlite3.connect("pul_toplaymiz.db"); users = conn.execute("SELECT id, name FROM users").fetchall()
        for u_id, u_name in users:
            kb = InlineKeyboardBuilder()
            for i in range(1, 11): kb.button(text=str(i), callback_data=f"rate_{i}")
            kb.adjust(5)
            try: await bot.send_message(u_id, f"Salom {u_name}, bizni baholang:", reply_markup=kb.as_markup())
            except: pass
        await call.message.answer("✅ Baholash posti yuborildi!")
    elif action == "3": await call.message.answer("Foydalanuvchi IDsini yozing:"); await state.set_state(Form.admin_msg_user_id)
    await call.answer()

@dp.message(Form.admin_post)
async def send_broad(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("pul_toplaymiz.db"); users = conn.execute("SELECT id FROM users").fetchall(); conn.close()
    for u in users:
        try: await bot.send_message(u[0], message.text)
        except: pass
    await message.answer("✅ Tarqatildi!"); await state.clear()

@dp.callback_query(F.data.startswith("rate_"))
async def handle_rating(call: types.CallbackQuery):
    rate = int(call.data.split("_")[1]); conn = sqlite3.connect("pul_toplaymiz.db")
    conn.execute("UPDATE users SET rating = rating + ? WHERE id=?", (rate, call.from_user.id))
    conn.commit(); conn.close(); await call.message.edit_text("Rahmat!")

@dp.message(F.text == "📈 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect("pul_toplaymiz.db"); total_users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    total_rates = conn.execute("SELECT sum(rating) FROM users").fetchone()[0] or 0
    jobs = conn.execute("SELECT job, salary, dream_name FROM users").fetchall(); conn.close()
    txt = f"👥 Foydalanuvchilar: {total_users}\n⭐ Jami ballar: {total_rates}\n\n"
    for j in jobs: txt += f"💼 {j[0]} | 💰 {j[1]} | 🎯 {j[2]}\n"
    await message.answer(txt)

@dp.callback_query(F.data.startswith("reply_"))
async def admin_reply_start(call: types.CallbackQuery, state: FSMContext):
    uid = call.data.split("_")[1]; await state.update_data(target=uid)
    await call.message.answer("Javobingizni yozing:"); await state.set_state(Form.admin_answer)

@dp.message(Form.admin_answer)
async def admin_reply_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try: await bot.send_message(data['target'], f"🔔 Admin javobi: {message.text}"); await message.answer("✅ Yuborildi!")
    except: await message.answer("Xatolik!"); await state.clear()

@dp.message(F.text == "👑 Premium obunachilar")
async def prem_users_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect("pul_toplaymiz.db"); prems = conn.execute("SELECT id, name, premium_date FROM users WHERE is_premium=1").fetchall(); conn.close()
    if not prems: return await message.answer("Premium foydalanuvchilar yo'q.")
    for p in prems:
        kb = InlineKeyboardBuilder(); kb.button(text="Premiumni olish", callback_data=f"take_prem_{p[0]}")
        await message.answer(f"👤 {p[1]} (ID: {p[0]})\n📅 Gacha: {p[2]}", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("take_prem_"))
async def take_premium(call: types.CallbackQuery):
    uid = call.data.split("_")[2]; conn = sqlite3.connect("pul_toplaymiz.db"); conn.execute("UPDATE users SET is_premium=0 WHERE id=?", (uid,))
    conn.commit(); conn.close(); await call.message.delete(); await call.answer("Olib tashlandi")

@dp.message(F.text == "⬅️ Bosh menyu")
async def to_main(message: types.Message): await message.answer("Bosh menyu", reply_markup=get_main_kb(message.from_user.id))

async def main(): keep_alive(); print("Bot ishga tushdi!"); await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): logging.error("Stopped")
